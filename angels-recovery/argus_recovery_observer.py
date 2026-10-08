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
    "fabric_health": "https://angels-workspace-fabric.agentify-cloudflare-public-read.workers.dev/health",
    "fleet_cadence": "https://angels-workspace-fabric.agentify-cloudflare-public-read.workers.dev/ceo-report",
    "foundation_source_postgres": "https://angels-ascr-standby.floot.app/_api/ascr-health",
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
    if name == "fabric_health":
        stamp = datetime.fromisoformat(body["time"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        valid = (http == 200 and body.get("service") == "angels-workspace-fabric"
                 and body.get("status") == "ok" and -60 <= age <= 900)
        return valid, {"status": body.get("status"),
                       "age_seconds": round(age),
                       "company_execution_certified": False}
    if name == "fleet_cadence":
        stamp = datetime.fromisoformat(body["generated_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        reports = body.get("reports", [])
        fresh = []
        for report in reports:
            last = (report.get("runtime") or {}).get("last_cycle_at")
            tick = datetime.fromisoformat(last.replace("Z", "+00:00"))
            fresh.append(-60 <= (datetime.now(timezone.utc) - tick).total_seconds() <= 900)
        counts_valid = all(
            isinstance((report.get("counts") or {}).get(k), int)
            and (report.get("counts") or {})[k] >= 0
            for report in reports for k in ("queued", "executing", "verified", "failures")
        )
        valid = (http == 200 and body.get("service") == "angels-ceo-report"
                 and body.get("chatgpt_hosts_ceos") is False
                 and body.get("reporting_cadence") == "5m"
                 and -60 <= age <= 900 and bool(reports)
                 and all(fresh) and counts_valid)
        return valid, {
            "age_seconds": round(age),
            "observed_roles": len(reports),
            "queued": sum(x["counts"]["queued"] for x in reports) if counts_valid else None,
            "executing": sum(x["counts"]["executing"] for x in reports) if counts_valid else None,
            "historical_verified": sum(x["counts"]["verified"] for x in reports) if counts_valid else None,
            "mission_handover_acked": False,
            "production_authority_certified": False,
        }
    if name == "foundation_source_postgres":
        stamp = datetime.fromisoformat(body["observed_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        caps = body.get("capabilities", [])
        valid = (
            http == 200 and body.get("ok") is True
            and body.get("schema") == "angels.ascr-carrier-health/v1"
            and body.get("carrier") == "floot-neon"
            and body.get("database") == "PASS"
            and isinstance(caps, list)
            and "state.relational.failover" in caps
            and body.get("authority_widened") is False
            and body.get("irreversible_external_effect") is False
            and -60 <= age <= 900
        )
        return valid, {
            "database_health": body.get("database"),
            "carrier": body.get("carrier"),
            "age_seconds": round(age),
            "native_pg_dump_verified": False,
            "native_pg_restore_certified": False,
            "worker_ack_proved": False,
            "authority_widened": False,
        }
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
