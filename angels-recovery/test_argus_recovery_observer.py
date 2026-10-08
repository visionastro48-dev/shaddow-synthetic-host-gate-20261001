#!/usr/bin/env python3
"""Offline, no-network fail-closed regression tests for the existing public ARGUS observer."""
import unittest
from datetime import datetime, timedelta, timezone

from argus_recovery_observer import check


def iso(seconds=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def fleet(tick_seconds=0, execution=0):
    return {
        "service": "angels-ceo-report",
        "generated_at": iso(),
        "reporting_cadence": "5m",
        "chatgpt_hosts_ceos": False,
        "reports": [{
            "runtime": {"last_cycle_at": iso(tick_seconds)},
            "counts": {"queued": 0, "executing": execution, "verified": 0, "failures": 0},
        }]
    }


class ARGUSFailClosed(unittest.TestCase):
    def test_fresh_existing_fabric_is_health_only(self):
        good, ev = check("fabric_health", 200, {
            "service": "angels-workspace-fabric", "status": "ok", "time": iso()
        })
        self.assertTrue(good)
        self.assertFalse(ev["company_execution_certified"])

    def test_stale_fabric_is_rejected(self):
        self.assertFalse(check("fabric_health", 200, {
            "service": "angels-workspace-fabric", "status": "ok", "time": iso(-1800)
        })[0])

    def test_bad_fabric_status_is_rejected(self):
        self.assertFalse(check("fabric_health", 200, {
            "service": "angels-workspace-fabric", "status": "degraded", "time": iso()
        })[0])

    def test_fresh_fleet_observation_not_an_ack(self):
        good, ev = check("fleet_cadence", 200, fleet(execution=2))
        self.assertTrue(good)
        self.assertEqual(ev["executing"], 2)
        self.assertFalse(ev["mission_handover_acked"])
        self.assertFalse(ev["production_authority_certified"])

    def test_stale_worker_tick_rejected(self):
        self.assertFalse(check("fleet_cadence", 200, fleet(-3600))[0])

    def test_untrusted_fleet_counts_rejected(self):
        bad = fleet()
        bad["reports"][0]["counts"]["executing"] = "3"
        self.assertFalse(check("fleet_cadence", 200, bad)[0])

    def test_fleet_faking_chatgpt_host_rejected(self):
        bad = fleet()
        bad["chatgpt_hosts_ceos"] = True
        self.assertFalse(check("fleet_cadence", 200, bad)[0])

    def test_headquarters_cannot_implicitly_promote_authority(self):
        self.assertFalse(check("headquarters", 200, {
            "ok": True, "schema": "angels.hq-control-health/v1",
            "hq_database": {"reachable": True},
            "canonical_company_control": "VERIFIED",
            "production_authority_migrated": True
        })[0])

    def test_readiness_not_false_positive_when_workers_resumed(self):
        self.assertFalse(check("readiness", 200, {
            "schema": "angels.company-recovery-readiness/v1",
            "decision": "RESUME_CANONICAL_WORKERS",
            "production_authority_migrated": True,
            "original_authority_grants_verified": True,
            "independent_single_writer_fencing_verified": True,
            "resumed_real_worker_receipts_verified": True,
        })[0])


    def _foundation_health(self):
        return {
            "ok": True,
            "schema": "angels.ascr-carrier-health/v1",
            "carrier": "floot-neon",
            "capabilities": ["compute.general", "state.relational.failover"],
            "database": "PASS",
            "observed_at": iso(),
            "authority_widened": False,
            "irreversible_external_effect": False,
        }

    def test_foundation_existing_postgres_is_health_only(self):
        good, evidence = check("foundation_source_postgres", 200, self._foundation_health())
        self.assertTrue(good)
        self.assertEqual(evidence["database_health"], "PASS")
        self.assertFalse(evidence["native_pg_dump_verified"])
        self.assertFalse(evidence["native_pg_restore_certified"])
        self.assertFalse(evidence["worker_ack_proved"])

    def test_foundation_postgres_stale_timestamp_denied(self):
        bad = self._foundation_health()
        bad["observed_at"] = iso(-3600)
        self.assertFalse(check("foundation_source_postgres", 200, bad)[0])

    def test_foundation_authority_widening_denied(self):
        bad = self._foundation_health()
        bad["authority_widened"] = True
        self.assertFalse(check("foundation_source_postgres", 200, bad)[0])

    def test_foundation_database_failure_denied(self):
        bad = self._foundation_health()
        bad["database"] = "FAIL"
        self.assertFalse(check("foundation_source_postgres", 503, bad)[0])

    def test_foundation_missing_failover_capability_denied(self):
        bad = self._foundation_health()
        bad["capabilities"] = ["compute.general"]
        self.assertFalse(check("foundation_source_postgres", 200, bad)[0])

    def test_foundation_health_cannot_allow_external_effects(self):
        bad = self._foundation_health()
        bad["irreversible_external_effect"] = True
        self.assertFalse(check("foundation_source_postgres", 200, bad)[0])


if __name__ == "__main__":
    unittest.main()
