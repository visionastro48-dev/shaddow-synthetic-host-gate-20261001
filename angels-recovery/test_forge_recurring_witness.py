#!/usr/bin/env python3
"""Offline, deterministic recurrence-witness acceptance tests."""
import hashlib
import unittest
from datetime import datetime, timezone
from forge_recurring_witness import validate_cycle, witness, API

NOW = datetime(2026, 10, 9, 12, 20, tzinfo=timezone.utc)
SOURCE = b"print('synthetic')\n"
SHA = hashlib.sha256(SOURCE).hexdigest()
RUN = {"id":37927160105,"event":"schedule","conclusion":"success","created_at":"2026-10-09T11:59:39Z","head_sha":"a"*40}
RECEIPT = {"schema":"angels.forge.durable-acceptance/v1","workflow_event":"schedule",
"workflow_run_id":RUN["id"],"workflow_source_sha":RUN["head_sha"],
"workflow_run_url":"https://github.com/visionastro48-dev/shaddow-synthetic-host-gate-20261001/actions/runs/"+str(RUN["id"]),
"model":"qwen3:4b-instruct","structured_tool_call":True,"verified_synthetic_cases":11,
"artifacts_sha256_checked":True,"no_production_authority":True,"gateway_enrolled":False,
"continuous_workforce_certified":False,"issued_github_mission":None,"source_sha256":SHA,
"generation_attempts":1}

class WitnessTests(unittest.TestCase):
    def test_valid_bounded_schedule(self):
        self.assertEqual(validate_cycle(RUN, RECEIPT, SOURCE, NOW), (True,"bounded_schedule_cycle_verified"))
    def test_push_not_schedule(self):
        self.assertFalse(validate_cycle({**RUN,"event":"push"},RECEIPT,SOURCE,NOW)[0])
    def test_run_identity_mismatch(self):
        self.assertEqual(validate_cycle(RUN,{**RECEIPT,"workflow_run_id":999},SOURCE,NOW)[1],"contract_workflow_run_id")
    def test_receipt_url_mismatch(self):
        self.assertEqual(validate_cycle(RUN,{**RECEIPT,"workflow_run_url":"https://example.org/other"},SOURCE,NOW)[1],"run_url_mismatch")
    def test_source_tamper(self):
        self.assertEqual(validate_cycle(RUN,RECEIPT,b"tampered",NOW)[1],"source_hash_mismatch")
    def test_false_authority(self):
        self.assertEqual(validate_cycle(RUN,{**RECEIPT,"gateway_enrolled":True},SOURCE,NOW)[1],"contract_gateway_enrolled")
    def test_stale(self):
        self.assertEqual(validate_cycle(RUN,RECEIPT,SOURCE,datetime(2026,10,10,12,tzinfo=timezone.utc))[1],"outside_six_hour_window")
    def test_no_paid_model(self):
        self.assertEqual(validate_cycle(RUN,{**RECEIPT,"model":"paid"},SOURCE,NOW)[1],"contract_model")

if __name__=="__main__":
    unittest.main()
