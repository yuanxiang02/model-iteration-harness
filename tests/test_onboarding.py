"""Project onboarding gates; all human approvals here are simulated fixtures."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_harness as fixtures
from mih import core, onboarding, scoring
from mih.storage import HarnessError, load, save


class ProjectWorkflow(unittest.TestCase):
    setUp = fixtures.HarnessLifecycle.setUp
    tearDown = fixtures.HarnessLifecycle.tearDown

    def register(self, coupled=False, evaluate=True):
        evaluations = ["train.py"] if coupled else [str(Path(scoring.__file__).resolve())] if evaluate else []
        assessed = onboarding.inspect(self.store, self.repo, ["train.py"], evaluations)
        self.project = assessed["id"]
        save(self.path, self.config)
        return assessed

    def draft(self, protected=()):
        return onboarding.draft(self.store, self.project, self.path, protected)

    def approve_fixture(self):
        current = onboarding.state(self.store, self.project)
        return onboarding.approve(self.store, self.project, current["spec_digest"], "simulated-fixture-reviewer")

    def iterate(self):
        result = onboarding.iterate(self.store, self.project, "Use a feature rather than a constant prediction",
                                    factors=["prediction_rule: constant -> input feature"])
        self.experiments.append(result["id"])
        return result

    def test_inspection_is_read_only_and_shared_entry_requires_split(self):
        original = (self.repo / "train.py").read_bytes()
        assessed = self.register(coupled=True)
        self.assertEqual(assessed["analysis"]["finding"], "split-required")
        self.assertEqual((self.repo / "train.py").read_bytes(), original)
        self.assertEqual(core.git(self.repo, "status", "--porcelain"), b"")
        self.assertEqual(list(self.store.runs.iterdir()), [])
        self.assertTrue(Path(assessed["decoupling_plan"]).is_file())

    def test_missing_evaluation_is_uncertain_not_independence_claim(self):
        assessed = self.register(evaluate=False)
        self.assertEqual(assessed["analysis"]["finding"], "uncertain")

    def test_iteration_and_legacy_create_block_before_user_review(self):
        self.register()
        current = self.draft()
        self.assertEqual(current["stage"], "awaiting_review")
        self.assertTrue(Path(current["boundaries"]).is_file())
        self.assertEqual(list(self.store.runs.iterdir()), [])
        with self.assertRaisesRegex(HarnessError, "awaiting user review"):
            self.iterate()
        with self.assertRaisesRegex(HarnessError, "awaiting user review"):
            core.create(self.store, self.path)
        self.assertEqual(list(self.store.runs.iterdir()), [])

    def test_existing_manual_candidate_cannot_bypass_new_project_review(self):
        save(self.path, self.config)
        experiment = core.create(self.store, self.path)
        self.experiments.append(experiment["id"])
        self.register()
        self.draft()
        with self.assertRaisesRegex(HarnessError, "awaiting user review"):
            core.submit(self.store, experiment["id"])
        self.approve_fixture()
        with self.assertRaisesRegex(HarnessError, "predates project review"):
            core.submit(self.store, experiment["id"])

    def test_approval_binds_exact_markdown_and_spec(self):
        self.register()
        current = self.draft()
        with self.assertRaisesRegex(HarnessError, "digest differs"):
            onboarding.approve(self.store, self.project, "not-the-digest", "fixture")
        Path(current["boundaries"]).write_text(Path(current["boundaries"]).read_text() + "\nChanged review text.\n")
        with self.assertRaisesRegex(HarnessError, "digest differs"):
            onboarding.approve(self.store, self.project, current["spec_digest"], "fixture")

    def test_approved_project_completes_existing_experiment_lifecycle(self):
        self.register()
        self.draft()
        self.approve_fixture()
        experiment = self.iterate()
        self.assertEqual(experiment["project"]["project"], self.project)
        workspace = Path(experiment["workspace"])
        (workspace / "train.py").write_text(fixtures.TRAIN.replace('MODE = "baseline"', 'MODE = "candidate"'))
        core.submit(self.store, experiment["id"])
        result = core.wait(self.store, experiment["id"], 25)
        self.assertEqual(result["status"], "accepted", result)
        self.assertTrue(core.promote(self.store, experiment["id"])["ready"])

    def test_protected_path_wins_over_allowed_path(self):
        self.config["source"]["allowed_paths"].append("protected.py")
        self.register()
        self.draft(["protected.py"])
        self.approve_fixture()
        experiment = self.iterate()
        (Path(experiment["workspace"]) / "protected.py").write_text("# agent tried changing protected code\n")
        with self.assertRaisesRegex(HarnessError, "Out-of-scope"):
            core.submit(self.store, experiment["id"])

    def test_policy_change_cannot_bypass_review_via_legacy_contract(self):
        self.register()
        self.draft()
        self.approve_fixture()
        changed = copy.deepcopy(self.config)
        changed["execution"]["timeout_seconds"] += 1
        save(self.path, changed)
        with self.assertRaisesRegex(HarnessError, "changes the approved contract"):
            core.create(self.store, self.path)

    def test_fixed_reference_change_invalidates_approval(self):
        self.register()
        self.draft()
        self.approve_fixture()
        self.reference.write_text('{"id":"forged","target":0}\n')
        with self.assertRaisesRegex(HarnessError, "Fixed reference changed"):
            self.iterate()

    def test_edited_contract_cannot_keep_unrelated_frozen_reference_metadata(self):
        self.register()
        current = self.draft()
        replacement = self.root / "replacement-reference.jsonl"
        replacement.write_text('{"id":"a","target":1}\n')
        spec = load(current["specification"])
        spec["contract"]["evaluation"]["reference"] = str(replacement)
        save(current["specification"], spec)
        with self.assertRaisesRegex(HarnessError, "references disagree"):
            self.approve_fixture()

    def test_review_document_drift_blocks_existing_candidate_submission(self):
        self.register()
        current = self.draft()
        self.approve_fixture()
        experiment = self.iterate()
        Path(current["boundaries"]).write_text("# replaced after approval\n")
        with self.assertRaisesRegex(HarnessError, "specification changed"):
            core.submit(self.store, experiment["id"])

    def test_new_draft_does_not_reuse_old_approval(self):
        self.register()
        first = self.draft()
        self.approve_fixture()
        second = self.draft(["protected.py"])
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertTrue(Path(first["specification"]).is_file())
        with self.assertRaisesRegex(HarnessError, "awaiting user review"):
            self.iterate()

    def test_refresh_preserves_history_and_resets_review(self):
        self.register()
        first = self.draft()
        self.approve_fixture()
        assessed = onboarding.inspect(self.store, self.repo, ["train.py"], [], refresh=True)
        self.assertEqual(assessed["stage"], "assessed")
        self.assertTrue(Path(first["specification"]).is_file())
        self.assertTrue(list((Path(assessed["directory"]) / "history").iterdir()))
        with self.assertRaisesRegex(HarnessError, "Draft a boundary"):
            self.iterate()

    def test_still_shared_trusted_scorer_cannot_be_approved(self):
        self.register(coupled=True)
        self.config["evaluation"]["evaluator"] = str(self.repo / "train.py")
        save(self.path, self.config)
        with self.assertRaisesRegex(HarnessError, "still shares a training entry"):
            self.draft()

    def test_required_split_needs_matching_comparison_and_preserves_failed_exports(self):
        self.register(coupled=True)
        self.draft()
        with self.assertRaisesRegex(HarnessError, "no before/after"):
            self.approve_fixture()
        before, after = self.root / "before.jsonl", self.root / "after.jsonl"
        before.write_text('{"id":"a","prediction":0}\n{"id":"b","prediction":1}\n')
        after.write_text('{"id":"a","prediction":1}\n{"id":"b","prediction":1}\n')
        failed = onboarding.compare_split(self.store, self.project, before, after)
        self.assertFalse(failed["equivalent"])
        with self.assertRaisesRegex(HarnessError, "comparison failed"):
            self.approve_fixture()
        after.write_text('{"id":"b","prediction":1}\n{"id":"a","prediction":0}\n')
        passed = onboarding.compare_split(self.store, self.project, before, after)
        self.assertTrue(passed["equivalent"])
        current = self.approve_fixture()
        self.assertEqual(current["stage"], "approved")
        revision = Path(current["specification"]).parent
        self.assertTrue((revision / failed["evidence"] / "comparison.json").exists())
        (revision / passed["evidence"] / "before.jsonl").write_text("tampered")
        with self.assertRaisesRegex(HarnessError, "comparison evidence changed"):
            self.iterate()

    def test_cli_reports_pending_review_and_structured_iteration_error(self):
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        command = [sys.executable, "-m", "mih", "--state", str(self.store.root)]
        inspection = subprocess.run([*command, "project", "inspect", str(self.repo), "--train", "train.py"], env=env, capture_output=True, text=True)
        self.assertEqual(inspection.returncode, 0, inspection.stderr)
        identifier = json.loads(inspection.stdout)["id"]
        save(self.path, self.config)
        draft = subprocess.run([*command, "project", "draft", identifier, str(self.path)], env=env, capture_output=True, text=True)
        self.assertEqual(draft.returncode, 0, draft.stderr)
        self.assertEqual(json.loads(draft.stdout)["stage"], "awaiting_review")
        blocked = subprocess.run([*command, "iterate", identifier, "--hypothesis", "A declared improvement"], env=env, capture_output=True, text=True)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("awaiting user review", json.loads(blocked.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
