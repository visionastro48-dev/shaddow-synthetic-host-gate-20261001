#!/usr/bin/env python3
"""ANGELS public, credential-free infrastructure recovery observer.

Read-only witness only. Never authorizes mission work, writes state, or treats
an available carrier as the canonical company. Intended for the preexisting
public GitHub runner while private-repo Actions execution is unavailable.
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/angels-cloud-fabric"
ENDPOINTS = {
    "supervisor": "https://angels-cloud-supervisor.agentify-cloudflare-public-read.workers.dev/status",
    "headquarters": "https://angels-hq.lovable.app/api/control/health",
    "fabric_route": ROOT + "/ascr-route?capability=control.observability.readonly",
    "readiness": ROOT + "/company-recovery-readiness",
}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_json(name, url):
    req = urllib.request.Request(
        url, method="GET",
        headers={"Accept": "application/json",
                 "Cache-Control": "no-cache",
                 "User-Agent": "ANGELS-ARGUS-ReadOnlyRecovery/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            status, data = response.status, response.read(32_768)
    except urllib.error.HTTPError as error:
        status, data = error.code, error.read(32_768)
    return status, json.loads(data.decode("utf-8"))


def check(name, http, body):
    if name == "supervisor":
        updated = body.get("state_updated_at", "")
        stamp = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        checks = body.get("checks", [])
        valid = (http == 200 and body.get("status") == "VALIDATED"
                 and body.get("source") == "cron-5m"
                 and body.get("railway_required") is False
                 and -60 <= age <= 900
                 and len(checks) >= 4
                 and all(x.get("ok") is True for x in checks))
        return valid, {"cycle": body.get("state_version"), "age_seconds": round(age),
                       "passed_checks": sum(x.get("ok") is True for x in checks)}
    if name == "headquarters":
        valid = (http == 200 and body.get("ok") is True
                 and body.get("schema") == "angels.hq-control-health/v1"
                 and body.get("hq_database", {}).get("reachable") is True
                 and body.get("canonical_company_control") == "UNVERIFIED"
                 and body.get("production_authority_migrated") is False)
        return valid, {"database_reachable": body.get("hq_database", {}).get("reachable"),
                       "canonical_company_control": body.get("canonical_company_control")}
    if name == "fabric_route":
        valid = (http == 200 and body.get("ok") is True
                 and body.get("schema") == "angels.ascr-route-decision/v1"
                 and body.get("selected", {}).get("id") == "cloudflare-supervisor"
                 and body.get("policy", {}).get("provider_is_authority") is False)
        return valid, {"selected": body.get("selected", {}).get("id")}
    if name == "readiness":
        valid = (http == 503 and body.get("schema") == "angels.company-recovery-readiness/v1"
                 and body.get("decision") == "HOLD_CANONICAL_WORKERS"
                 and body.get("production_authority_migrated") is False
                 and body.get("original_authority_grants_verified") is False
                 and body.get("independent_single_writer_fencing_verified") is False
                 and body.get("resumed_real_worker_receipts_verified") is False)
        return valid, {"decision": body.get("decision"),
                       "db_query_responded": body.get("canonical_database_query_responded")}
    return False, {}


def main():
    receipt = {
        "schema": "angels.argus-recovery-observer/v1",
        "observed_at": now(),
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "carrier": "github-public-existing-repo",
        "operation_class": "READ_ONLY",
        "credential_access": False,
        "mission_authority": False,
        "company_workers_resumed": False,
        "external_side_effects": False,
        "observations": {},
    }
    all_ok = True
    for name, url in ENDPOINTS.items():
        try:
            http, body = fetch_json(name, url)
            ok, evidence = check(name, http, body)
            receipt["observations"][name] = {"contract_pass": ok, "http": http,
                                              "evidence": evidence}
        except Exception as exc:
            ok = False
            receipt["observations"][name] = {"contract_pass": False,
                                              "error_type": type(exc).__name__}
        all_ok = all_ok and ok
    receipt["observer_contracts_pass"] = all_ok
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    receipt["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    print("ANGELS_ARGUS_READONLY_RECEIPT=" + json.dumps(receipt, sort_keys=True), flush=True)
    if not all_ok:
        print("ANGELS_ARGUS_OBSERVER=DEGRADED", file=sys.stderr)
        return 1
    print("ANGELS_ARGUS_OBSERVER=OBSERVATION_PASS; CANONICAL_WORKERS=HOLD", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
