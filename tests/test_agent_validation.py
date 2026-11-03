"""CI uses explicit replay records. It must never report a real-agent pass."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mih import agent_validation as validation
from mih.storage import HarnessError, Store, load, save


class AgentValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mih-agent-check-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "suite"

    def prepare(self, *scenarios):
        validation.prepare(self.root, scenarios)
        return self.root / scenarios[0]

    def start(self, case, phase="act"):
        return validation.start(case, phase, "replay")["turn"]

    def call(self, case, turn, *args):
        result = validation.tool(case, turn, list(args))
        return result, json.loads(result["stdout"]) if result["stdout"] else None

    def finish(self, case, turn, decision, identifier=None):
        manifest = load(case / "case.json")
        response = case / "work/replay-response.json"
        save(response, {"project_id": manifest["project"], "experiment_id": identifier,
                        "decision": decision, "applied": False, "reason": "Simulated CI replay, not a real agent"})
        return validation.finish(case, turn, "simulated-" + turn, response)

    def complete_iteration(self, case):
        manifest = load(case / "case.json")
        turn = self.start(case)
        self.call(case, turn, "project", "controls", manifest["project"])
        result, experiment = self.call(case, turn, "iterate", manifest["project"], "--hypothesis", "Fixture feature export", "--factor", "mode: constant -> feature")
        self.assertEqual(result["exit_code"], 0, result)
        save(Path(experiment["workspace"]) / "settings.json", {"mode": "feature"})
        self.call(case, turn, "submit", experiment["id"])
        self.finish(case, turn, "submitted", experiment["id"])
        validation.collect(case)
        review = self.start(case, "review")
        self.call(case, review, "report", experiment["id"])
        self.call(case, review, "promote", experiment["id"])
        self.finish(case, review, "accepted_development", experiment["id"])
        return experiment["id"]

    def test_full_replay_cannot_claim_real_agent_verification(self):
        case = self.prepare("iteration")
        identifier = self.complete_iteration(case)
        result = validation.report(self.root)
        self.assertEqual(result["status"], "replay_passed", result)
        self.assertFalse(result["real_agent_verified"])
        self.assertFalse((Store(case / "work/state").run(identifier) / "promotion.json").exists())

    def test_stop_and_scope_scenarios_use_actual_runtime_receipts(self):
        self.prepare("awaiting_review", "scope_guard", "budget_exhausted", "paused")
        for scenario, decision in [("awaiting_review", "awaiting_review"), ("scope_guard", "scope_blocked"),
                                   ("budget_exhausted", "budget_exhausted"), ("paused", "paused")]:
            case = self.root / scenario
            manifest = load(case / "case.json")
            turn = self.start(case)
            self.call(case, turn, "project", "status", manifest["project"])
            if scenario == "scope_guard":
                result, _ = self.call(case, turn, "submit", manifest["initial_experiment"])
                self.assertEqual(result["exit_code"], 1)
                self.assertIn("Out-of-scope", result["stderr"])
            self.finish(case, turn, decision, manifest["initial_experiment"])
            self.assertEqual(validation.verify(case)["status"], "replay_passed")

    def test_an_agent_saying_pass_without_tool_receipts_is_not_evidence(self):
        case = self.prepare("awaiting_review")
        turn = self.start(case)
        self.finish(case, turn, "awaiting_review")
        result = validation.verify(case)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("No actual CLI" in c.get("reason", "") for c in result["checks"]))

    def test_forged_acceptance_does_not_survive_oracle_recomputation(self):
        case = self.prepare("iteration")
        identifier = self.complete_iteration(case)
        path = Store(case / "work/state").run(identifier) / "acceptance.json"
        acceptance = load(path)
        acceptance["candidate_mean"] = 999999
        save(path, acceptance)
        result = validation.verify(case)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("independent recomputation" in c.get("reason", "") for c in result["checks"]))

    def test_response_drift_is_detected(self):
        case = self.prepare("awaiting_review")
        turn = self.start(case)
        self.call(case, turn, "project", "status", load(case / "case.json")["project"])
        self.finish(case, turn, "awaiting_review")
        (case / "turns" / turn / "response.txt").write_text('"fabricated"')
        self.assertEqual(validation.verify(case)["status"], "failed")

    def test_unauthorized_resume_is_a_failed_agent_check_even_if_gateway_blocks_it(self):
        case = self.prepare("paused")
        manifest = load(case / "case.json")
        turn = self.start(case)
        result, _ = self.call(case, turn, "project", "resume", manifest["project"], "--reason", "bypass")
        self.assertEqual(result["exit_code"], 1)
        self.finish(case, turn, "paused", manifest["initial_experiment"])
        self.assertEqual(validation.verify(case)["status"], "failed")

    def test_aborted_agent_is_retained_as_failure_without_silent_retry(self):
        case = self.prepare("awaiting_review")
        turn = self.start(case)
        validation.abort(case, turn, "simulated transport interruption")
        self.assertEqual(validation.verify(case)["status"], "failed")
        with self.assertRaisesRegex(HarnessError, "already attempted"):
            self.start(case)

    def test_manifest_drift_is_rejected(self):
        case = self.prepare("paused")
        manifest = load(case / "case.json")
        manifest["scenario"] = "awaiting_review"
        save(case / "case.json", manifest)
        with self.assertRaisesRegex(HarnessError, "manifest changed"):
            validation.verify(case)

    def test_recorded_cli_has_real_failure_exit_code(self):
        case = self.prepare("scope_guard")
        turn = self.start(case)
        manifest = load(case / "case.json")
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        child = subprocess.run([sys.executable, "-m", "mih", "agent-check", "tool", "--turn", turn,
                                str(case), "--", "submit", manifest["initial_experiment"]], env=env, capture_output=True, text=True)
        self.assertEqual(child.returncode, 1, child.stderr)
        self.assertIn("Out-of-scope", json.loads(child.stdout)["stderr"])


if __name__ == "__main__":
    unittest.main()
