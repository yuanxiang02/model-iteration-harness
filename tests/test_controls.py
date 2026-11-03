"""Controllability checks. All policy approvals here are simulated fixtures."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

import test_harness as fixtures
import test_onboarding as onboarding_fixtures
from mih import controls, core, onboarding
from mih.storage import HarnessError, load, save


class Controllability(unittest.TestCase):
    setUp = fixtures.HarnessLifecycle.setUp
    tearDown = fixtures.HarnessLifecycle.tearDown
    register = onboarding_fixtures.ProjectWorkflow.register
    approve_fixture = onboarding_fixtures.ProjectWorkflow.approve_fixture
    iterate = onboarding_fixtures.ProjectWorkflow.iterate

    def ready(self, **kwargs):
        self.register()
        current = onboarding.draft(self.store, self.project, self.path, **kwargs)
        self.approve_fixture()
        return current

    def change(self, experiment):
        (Path(experiment["workspace"]) / "train.py").write_text(
            fixtures.TRAIN.replace('MODE = "baseline"', 'MODE = "candidate"'))

    def test_default_round_limit_also_blocks_low_level_create(self):
        self.ready()
        self.iterate()
        with self.assertRaisesRegex(HarnessError, "budget exhausted"):
            core.create(self.store, self.path, factors=["bypass attempt"])
        current = controls.status(self.store, self.project)
        self.assertEqual((current["used"], current["remaining"]), (1, 0))
        self.assertFalse(current["can_create"])

    def test_active_slots_release_on_cancel_but_total_budget_does_not(self):
        self.ready(max_experiments=2)
        first = self.iterate()
        with self.assertRaisesRegex(HarnessError, "Active candidate limit"):
            self.iterate()
        core.cancel(self.store, first["id"])
        second = self.iterate()
        core.cancel(self.store, second["id"])
        current = controls.status(self.store, self.project)
        self.assertEqual(current["used"], 2)
        self.assertEqual(current["active"], [])
        with self.assertRaisesRegex(HarnessError, "budget exhausted"):
            self.iterate()

    def test_declared_factors_are_required_before_spending_budget(self):
        self.ready()
        with self.assertRaisesRegex(HarnessError, "Declare changed factors"):
            onboarding.iterate(self.store, self.project, "Missing factor")
        self.assertEqual(controls.status(self.store, self.project)["used"], 0)
        self.assertEqual(list(self.store.runs.iterdir()), [])

    def test_parallel_requests_cannot_overspend_last_slot(self):
        self.ready()
        def attempt(_):
            try:
                return onboarding.iterate(self.store, self.project, "Concurrent candidate", factors=["prediction rule"])
            except HarnessError as error:
                return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, range(2)))
        experiments = [value for value in outcomes if isinstance(value, dict)]
        self.experiments.extend(value["id"] for value in experiments)
        self.assertEqual(len(experiments), 1, outcomes)
        self.assertEqual(controls.status(self.store, self.project)["used"], 1)

    def test_pause_blocks_dispatch_and_resume_does_not_reset_budget(self):
        self.ready()
        experiment = self.iterate()
        self.change(experiment)
        controls.set_paused(self.store, self.project, True, "simulated operator pause")
        with self.assertRaisesRegex(HarnessError, "paused"):
            core.submit(self.store, experiment["id"])
        self.assertEqual(self.store.state(experiment["id"])["status"], "prepared")
        controls.set_paused(self.store, self.project, False, "simulated operator resume")
        self.assertEqual(controls.status(self.store, self.project)["remaining"], 0)
        core.submit(self.store, experiment["id"])
        self.assertEqual(core.wait(self.store, experiment["id"], 25)["status"], "accepted")

    def test_pause_drains_running_job_and_blocks_promotion(self):
        self.ready()
        experiment = self.iterate()
        self.change(experiment)
        core.submit(self.store, experiment["id"])
        controls.set_paused(self.store, self.project, True, "simulated pause while running")
        result = core.wait(self.store, experiment["id"], 25)
        self.assertEqual(result["status"], "accepted", result)
        with self.assertRaisesRegex(HarnessError, "paused"):
            core.promote(self.store, experiment["id"])
        controls.set_paused(self.store, self.project, False, "simulated resume for review")
        self.assertTrue(core.promote(self.store, experiment["id"])["ready"])

    def test_acceptance_stops_new_and_prepared_candidates_but_allows_promotion(self):
        self.ready(max_experiments=3, max_active=2)
        first, second = self.iterate(), self.iterate()
        self.change(first)
        self.change(second)
        core.submit(self.store, first["id"])
        self.assertEqual(core.wait(self.store, first["id"], 25)["status"], "accepted")
        with self.assertRaisesRegex(HarnessError, "stop_on_acceptance"):
            self.iterate()
        with self.assertRaisesRegex(HarnessError, "stop_on_acceptance"):
            core.submit(self.store, second["id"])
        self.assertTrue(core.promote(self.store, first["id"])["ready"])

    def test_declaration_tampering_is_rejected_before_dispatch(self):
        self.ready()
        experiment = self.iterate()
        self.change(experiment)
        save(self.store.run(experiment["id"]) / "declaration.json", {"factors": ["forged"]})
        with self.assertRaisesRegex(HarnessError, "Frozen declaration"):
            core.submit(self.store, experiment["id"])

    def test_failed_materialization_consumes_a_slot_and_preserves_failure(self):
        self.ready()
        patch = self.root / "bad.patch"
        patch.write_text("not a valid patch")
        with self.assertRaises(HarnessError):
            onboarding.iterate(self.store, self.project, "Invalid fixture patch", patch, ["prediction rule"])
        current = controls.status(self.store, self.project)
        self.assertEqual((current["used"], current["remaining"]), (1, 0))
        record = current["experiments"][0]
        self.experiments.append(record["id"])
        self.assertEqual(record["status"], "failed")
        self.assertTrue((self.store.run(record["id"]) / "proposed.patch").is_file())

    def test_legacy_specification_requires_new_review_for_new_candidates(self):
        self.register()
        current = onboarding.draft(self.store, self.project, self.path)
        spec = load(current["specification"])
        spec.pop("iteration_policy")
        spec["schema_version"] = 1
        save(current["specification"], spec)
        self.approve_fixture()  # Simulated historical policy; never a real user approval.
        with self.assertRaisesRegex(HarnessError, "Legacy specification"):
            self.iterate()
        self.assertFalse(controls.status(self.store, self.project)["can_create"])

    def test_new_revision_keeps_prior_active_work_and_operator_pause_visible(self):
        self.ready(max_experiments=2)
        first = self.iterate()
        controls.set_paused(self.store, self.project, True, "simulated operator pause")
        onboarding.draft(self.store, self.project, self.path, max_experiments=2)
        self.approve_fixture()
        current = controls.status(self.store, self.project)
        self.assertTrue(current["operator_control"]["paused"])
        self.assertEqual(current["prior_active"][0]["id"], first["id"])
        controls.set_paused(self.store, self.project, False, "simulated operator resume")
        with self.assertRaisesRegex(HarnessError, "Active candidate limit"):
            self.iterate()
        core.cancel(self.store, first["id"])
        self.iterate()
        self.assertEqual(controls.status(self.store, self.project)["used"], 1)

    def test_total_wall_budget_covers_multiple_individually_short_commands(self):
        slow = "import time\ntime.sleep(0.3)\n" + fixtures.TRAIN
        (self.repo / "train.py").write_text(slow)
        core.git(self.repo, "add", "train.py")
        core.git(self.repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "slow fixture")
        self.config["execution"]["total_timeout_seconds"] = 1
        save(self.path, self.config)
        experiment = core.create(self.store, self.path)
        self.experiments.append(experiment["id"])
        (Path(experiment["workspace"]) / "train.py").write_text(slow.replace('MODE = "baseline"', 'MODE = "candidate"'))
        core.submit(self.store, experiment["id"])
        result = core.wait(self.store, experiment["id"], 15)
        self.assertEqual(result["status"], "timed_out", result)
        self.assertIn("total wall-clock", result["error"])
        self.assertNotIn("acceptance", result)
        self.assertTrue(list(self.store.run(experiment["id"]).glob("*-train.log")))

    def test_separate_cli_process_observes_budget_and_stop_reasons(self):
        self.ready()
        self.iterate()
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        output = subprocess.check_output([sys.executable, "-m", "mih", "--state", str(self.store.root),
                                          "project", "controls", self.project], env=env, text=True)
        current = json.loads(output)
        self.assertEqual(current["used"], 1)
        self.assertTrue(any("budget exhausted" in reason for reason in current["blocked_reasons"]))

    def test_cancellation_during_acceptance_does_not_publish_a_pass(self):
        self.config["acceptance"]["bootstrap_samples"] = 100000
        save(self.path, self.config)
        experiment = core.create(self.store, self.path)
        self.experiments.append(experiment["id"])
        self.change(experiment)
        core.submit(self.store, experiment["id"])
        deadline = time.monotonic() + 20
        state = self.store.state(experiment["id"])
        while state["status"] not in core.TERMINAL and state["status"] != "accepting" and time.monotonic() < deadline:
            time.sleep(.005)
            state = self.store.state(experiment["id"])
        self.assertEqual(state["status"], "accepting", state)
        core.cancel(self.store, experiment["id"])
        result = core.wait(self.store, experiment["id"], 10)
        self.assertEqual(result["status"], "cancelled", result)
        self.assertNotIn("acceptance", result)


if __name__ == "__main__":
    unittest.main()
