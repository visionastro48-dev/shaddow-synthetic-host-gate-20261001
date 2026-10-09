#!/usr/bin/env python3
"""Independent deterministic tests for an isolated second FORGE coding mission."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).with_name("forge-lease-guard-lab.py")
spec = importlib.util.spec_from_file_location("forge_lease_lab", path)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)

REFERENCE = r'''
import json, sys

REQUIRED={"mission_id","writer_id","claim_epoch","external_effects_allowed","nonce"}
def main():
    try:
        if len(sys.argv)!=2:
            raise ValueError("args")
        with open(sys.argv[1], encoding="utf-8") as file:
            d=json.load(file)
        if not isinstance(d,dict) or set(d.keys()) != REQUIRED:
            raise ValueError("keys")
        if type(d["mission_id"]) is not str or d["mission_id"]!="FORGE-LEASE-002":
            raise ValueError("mission")
        if type(d["writer_id"]) is not str or d["writer_id"]!="foundation-worker-1":
            raise ValueError("writer")
        if type(d["claim_epoch"]) is not int or not 1<=d["claim_epoch"]<=9999:
            raise ValueError("epoch")
        if type(d["external_effects_allowed"]) is not bool or d["external_effects_allowed"] is not False:
            raise ValueError("effects")
        nonce=d["nonce"]
        if type(nonce) is not str or len(nonce)!=16 or any(char not in "0123456789abcdef" for char in nonce):
            raise ValueError("nonce")
    except Exception:
        print("BLOCKED")
        sys.exit(2)
    print("CLAIM_OK")
    sys.exit(0)
if __name__=="__main__":
    main()
'''

class IndependentLeaseTests(unittest.TestCase):
    def test_reference_passes_all_eighteen_cases(self):
        with tempfile.TemporaryDirectory() as td:
            candidate=Path(td)/"lease_verify.py"
            candidate.write_text(REFERENCE)
            lab.scan_code(REFERENCE)
            passed,total,issues=lab.assess(candidate,Path(td))
            self.assertEqual((passed,total,issues),(18,18,[]))

    def test_bool_as_int_fails_real_acceptance(self):
        weak=REFERENCE.replace('type(d["claim_epoch"]) is not int', 'not isinstance(d["claim_epoch"],int)')
        self.assertNotEqual(weak,REFERENCE)
        with tempfile.TemporaryDirectory() as td:
            candidate=Path(td)/"lease_verify.py"
            candidate.write_text(weak)
            passed,total,issues=lab.assess(candidate,Path(td))
            self.assertLess(passed,total)
            self.assertTrue(any("epoch_bool" in item for item in issues),issues)

    def test_extra_keys_fail_closed(self):
        weak=REFERENCE.replace('set(d.keys()) != REQUIRED','not REQUIRED.issubset(set(d.keys()))')
        self.assertNotEqual(weak,REFERENCE)
        with tempfile.TemporaryDirectory() as td:
            candidate=Path(td)/"lease_verify.py"
            candidate.write_text(weak)
            passed,total,issues=lab.assess(candidate,Path(td))
            self.assertLess(passed,total)
            self.assertTrue(any("extra" in item for item in issues),issues)

    def test_source_import_restrictions(self):
        with self.assertRaises(ValueError):
            lab.scan_code(REFERENCE+"\nimport os\n")
        with self.assertRaises(ValueError):
            lab.scan_code(REFERENCE+"\nexec('pass')\n")

if __name__=="__main__":
    unittest.main()
