#!/usr/bin/env python3
"""Credential-free, GET-only diagnostic observer for legacy ANGELS services.

No scheduler is created here; this module is run by the existing ANGELS ARGUS
GitHub Actions worker. Healthy transport is not evidence of recovered data,
worker authority, customers, or mission execution.
"""
from __future__ import annotations
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

SOURCES = {
    "edge": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/angels-cloud-fabric/runtime-health",
    "readiness": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/angels-cloud-fabric/company-recovery-readiness",
    "octopus": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/octopus-public-proof/health",
    "aether": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/angels-peer-probe/swarmmemo/webhook/status",
}


def get_public_status(url):
    request = urllib.request.Request(url, method="GET", headers={
        "Accept": "application/json", "Cache-Control": "no-cache",
        "User-Agent": "ANGELS-ARGUS-FailClosed-ReadOnly/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as resp:
            status, data = resp.status, resp.read(16385)
    except urllib.error.HTTPError as err:
        status, data = err.code, err.read(16385)
    if len(data) > 16384:
        raise ValueError("oversized_response")
    obj = json.loads(data.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("non_object_json")
    return status, obj


def classify(name, status, obj):
    """All classifications describe an observation, never authorize an effect."""
    if name == "edge":
        good = (status == 200 and obj.get("ok") is True and
                obj.get("schema") == "angels.shared-runtime/v1" and
                obj.get("writes") is False)
        return ("READONLY_COMPUTE_REACHABLE" if good else "UNKNOWN_OR_INVALID",
                {"transport_validated": good, "production_authority": False})
    if name == "readiness":
        fail_closed = (status == 503 and obj.get("ok") is False and
                       obj.get("schema") == "angels.company-recovery-readiness/v1" and
                       obj.get("decision") == "HOLD_CANONICAL_WORKERS" and
                       obj.get("production_authority_migrated") is False and
                       obj.get("resumed_real_worker_receipts_verified") is False and
                       obj.get("independent_single_writer_fencing_verified") is False)
        return ("HOLD_CONFIRMED" if fail_closed else "UNKNOWN_OR_INVALID",
                {"hold_confirmed": fail_closed, "database_query_responded":
                    obj.get("canonical_database_query_responded") if fail_closed else None,
                 "production_authority": False})
    if name == "octopus":
        good = (status == 200 and obj.get("ok") is True and
                obj.get("service") == "octopus-public-proof" and
                obj.get("read_only") is True and isinstance(obj.get("durable_truth"), dict) and
                obj.get("source", {}).get("promoted") is False)
        truth = obj.get("durable_truth") or {}
        availability = truth.get("available") if good else None
        result = ("TRUTH_AVAILABLE_UNCERTIFIED" if availability is True else
                  "DURABLE_TRUTH_UNAVAILABLE" if availability is False else
                  "UNKNOWN_OR_INVALID")
        return result, {"health_response_validated": good,
                        "durable_truth_available": availability,
                        "customers_or_payments_verified": False,
                        "production_authority": False}
    if name == "aether":
        good = (status == 200 and obj.get("ok") is True and
                obj.get("schema") == "aether.swarmmemo-webhook/v1" and
                obj.get("event_actions_enabled") is False)
        return ("EVENT_ACTIONS_DISABLED" if good else "UNKNOWN_OR_INVALID",
                {"explicitly_disabled": good, "event_verification_ready":
                    obj.get("event_verification_ready") if good else None,
                 "production_authority": False})
    raise ValueError("unrecognized_probe")


def collect(probe=get_public_status):
    entries = {}
    for name, url in SOURCES.items():
        try:
            status, body = probe(url)
            classification, evidence = classify(name, status, body)
            entries[name] = {"http": status, "classification": classification,
                             "evidence": evidence}
        except (ValueError, UnicodeError, TimeoutError, OSError, urllib.error.URLError) as err:
            entries[name] = {"http": None, "classification": "UNKNOWN_OR_INVALID",
                             "evidence": {"error_type": type(err).__name__,
                                          "production_authority": False}}
    verified = all(row["classification"] != "UNKNOWN_OR_INVALID"
                   for row in entries.values())
    return {"schema": "angels.argus.failclosed-live-truth-observer/v1",
            "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "observer_result": "OBSERVATION_PASS" if verified else "PARTIAL_UNKNOWN",
            "gates": entries,
            "company_execution_certified": False,
            "original_postgres_native_restore_certified": False,
            "external_effects_enabled": False,
            "historical_missions_replayed": False}


def main():
    report = collect()
    serialized = json.dumps(report, sort_keys=True, separators=(",", ":"))
    print("ARGUS_LIVE_TRUTH_RECEIPT " + serialized)
    print("ARGUS_LIVE_TRUTH_SHA256 " + hashlib.sha256(serialized.encode()).hexdigest())
    return 0 if report["observer_result"] == "OBSERVATION_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())