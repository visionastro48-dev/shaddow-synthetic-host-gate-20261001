#!/usr/bin/env python3
"""Independent, offline acceptance tests for no-authority FORGE evidence persistence."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("forge-evidence-publish.py")
spec = importlib.util.spec_from_file_location("forge_evidence_publish", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA = "a" * 40
RID = "37921919891"
SOURCE = b"import json\nimport sys\nprint('BLOCKED')\n" * 4


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.artifact = self.root / "artifact"
        self.repo = self.root / "repo"
        self.artifact.mkdir()
        self.repo.mkdir()
        self.data = {
            "schema": "angels.forge.real-local-model-coding/v1",
            "outcome": "REAL_MODEL_CODE_ACCEPTED",
            "model": "qwen3:4b-instruct",
            "tool_call_real": True,
            "authority": "none",
            "legacy_data_mounted": False,
            "gateway_enrolled": False,
            "continuous_workforce_certified": False,
            "attempts": 1,
            "independent_tests_passed": 11,
            "independent_tests_total": 11,
            "source_sha256": hashlib.sha256(SOURCE).hexdigest(),
        }
        (self.artifact / "gate_verify.py").write_bytes(SOURCE)
        self.write_receipt()

    def write_receipt(self):
        (self.artifact / "acceptance.json").write_text(json.dumps(self.data))

    def do_publish(self, **overrides):
        kwargs = dict(artifact_dir=self.artifact, repo_root=self.repo,
                      run_id=RID, run_attempt="1", event="push", head_sha=SHA)
        kwargs.update(overrides)
        return mod.publish(**kwargs)

    def test_acceptance_and_idempotent_replay(self):
        target = self.do_publish()
        first = (target / "receipt.json").read_bytes()
        self.assertEqual((target / "gate_verify.py").read_bytes(), SOURCE)
        self.assertTrue(json.loads(first)["no_production_authority"])
        self.assertEqual(self.do_publish(), target)
        # Same evidence on a subsequent GitHub Actions run attempt is a no-op.
        self.assertEqual(self.do_publish(run_attempt="2"), target)
        self.assertEqual((target / "receipt.json").read_bytes(), first)

    def test_tampered_source_is_rejected(self):
        (self.artifact / "gate_verify.py").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "source_digest_mismatch"):
            self.do_publish()

    def test_false_authority_claim_is_rejected(self):
        self.data["gateway_enrolled"] = True
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, "acceptance_contract_gateway_enrolled"):
            self.do_publish()

    def test_extra_artifact_is_rejected(self):
        (self.artifact / "unexpected").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "artifact_file_set_mismatch"):
            self.do_publish()

    def test_symlink_source_is_rejected(self):
        (self.artifact / "gate_verify.py").unlink()
        (self.artifact / "gate_verify.py").symlink_to(self.artifact / "acceptance.json")
        with self.assertRaisesRegex(ValueError, "untrusted_file_type_or_size"):
            self.do_publish()

    def test_conflicting_replay_is_rejected(self):
        self.do_publish()
        changed = SOURCE + b"# competing source\\n"
        (self.artifact / "gate_verify.py").write_bytes(changed)
        self.data["source_sha256"] = hashlib.sha256(changed).hexdigest()
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, "conflicting_replay"):
            self.do_publish(run_attempt="2")

    def test_invalid_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_run_id"):
            self.do_publish(run_id="../broken")
        with self.assertRaisesRegex(ValueError, "unsupported_event"):
            self.do_publish(event="pull_request")


if __name__ == "__main__":
    unittest.main()
