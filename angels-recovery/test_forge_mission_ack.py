#!/usr/bin/env python3
"""Offline no-authority GitHub mission acknowledgement contract checks."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("forge_mission_ack",HERE/"forge_mission_ack.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
RUN_ID="37927160105"
ISSUE=17
SHA=hashlib.sha256(b"synthetic-test-source").hexdigest()

class AckTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.event_path=root/"event.json"
        self.receipt_path=root/"receipt.json"
        self.out_path=root/"ack.txt"
        self.event={"action":"opened","repository":{"full_name":mod.REPO},
                    "issue":{"number":ISSUE,"user":{"login":mod.OWNER},
                             "title":mod.TITLE,"body":"mission_id="+mod.MISSION}}
        self.receipt={"schema":"angels.forge.durable-acceptance/v1",
                      "workflow_event":"issues",
                      "workflow_run_id":int(RUN_ID),
                      "workflow_run_attempt":1,
                      "workflow_run_url":mod.ROOT+"/actions/runs/"+RUN_ID,
                      "source_sha256":SHA,
                      "structured_tool_call":True,
                      "verified_synthetic_cases":11,
                      "artifacts_sha256_checked":True,
                      "no_production_authority":True,
                      "gateway_enrolled":False,
                      "continuous_workforce_certified":False,
                      "issued_github_mission":{"mission_id":mod.MISSION,"github_issue_number":ISSUE,
                                               "issuer":"github-repository-owner",
                                               "angels_gateway_authorized":False}}
    def run_ack(self,attempt="1"):
        self.event_path.write_text(json.dumps(self.event))
        self.receipt_path.write_text(json.dumps(self.receipt))
        return mod.ack(self.event_path,self.receipt_path,RUN_ID,attempt,mod.REPO,self.out_path)
    def test_valid_mission_ack_is_deterministic(self):
        marker=self.run_ack()
        self.assertIn("ANGELS_FORGE_GITHUB_ACK:run=",marker)
        txt=self.out_path.read_text()
        self.assertIn("NOT",txt.upper())
        self.assertIn("not** ANGELS Gateway",txt)
        self.assertIn(marker,txt)
        self.assertEqual(self.run_ack("2"),marker)
    def test_nonowner_rejected(self):
        self.event["issue"]["user"]["login"]="someone-else"
        with self.assertRaisesRegex(ValueError,"untrusted_issue"):self.run_ack()
    def test_tampered_prompt_rejected(self):
        self.event["issue"]["body"]="please run private work"
        with self.assertRaisesRegex(ValueError,"untrusted_issue"):self.run_ack()
    def test_wrong_issue_rejected(self):
        self.receipt["issued_github_mission"]["github_issue_number"]=18
        with self.assertRaisesRegex(ValueError,"mission_binding_mismatch"):self.run_ack()
    def test_false_gateway_enrollment_rejected(self):
        self.receipt["gateway_enrolled"]=True
        with self.assertRaisesRegex(ValueError,"receipt_contract_gateway_enrolled"):self.run_ack()
    def test_wrong_run_rejected(self):
        self.receipt["workflow_run_id"]=12345
        with self.assertRaisesRegex(ValueError,"receipt_contract_workflow_run_id"):self.run_ack()
    def test_skipped_receipt_rejected(self):
        self.receipt["verified_synthetic_cases"]=0
        with self.assertRaisesRegex(ValueError,"receipt_contract_verified_synthetic_cases"):self.run_ack()
    def test_future_attempt_rejected(self):
        self.receipt["workflow_run_attempt"]=2
        with self.assertRaisesRegex(ValueError,"invalid_recorded_attempt"):self.run_ack()
    def test_invalid_source_digest_rejected(self):
        self.receipt["source_sha256"]="wrong"
        with self.assertRaisesRegex(ValueError,"invalid_source_sha"):self.run_ack()
    def test_unexpected_event_rejected(self):
        self.event["action"]="edited"
        with self.assertRaisesRegex(ValueError,"untrusted_issue"):self.run_ack()

if __name__=="__main__":
    unittest.main()
