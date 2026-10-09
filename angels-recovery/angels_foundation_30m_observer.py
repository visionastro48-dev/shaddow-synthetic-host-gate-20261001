#!/usr/bin/env python3
"""Public, credential-free ANGELS observer. No model, execution authority, or production writes."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

ENDPOINTS = {
    "supervisor": "https://angels-cloud-supervisor.agentify-cloudflare-public-read.workers.dev/status",
    "hq": "https://angels-hq.lovable.app/api/control/health",
    "recovery": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/angels-cloud-fabric/company-recovery-readiness",
    "edge": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/angels-cloud-fabric/runtime-health",
    "octopus": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/octopus-public-proof/health",
    "aether": "https://yztkpjvkpqdfhltjqbzx.supabase.co/functions/v1/angels-peer-probe/swarmmemo/webhook/status",
}

def fetch(name, url):
    assert ENDPOINTS[name] == url
    request = urllib.request.Request(url, headers={"Accept": "application/json", "Cache-Control": "no-cache", "User-Agent": "ANGELS-ReadonlyHourly/1.0"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=13) as res:
            status = res.status
            raw = res.read(16384)
    except urllib.error.HTTPError as ex:
        status = ex.code
        raw = ex.read(16384)
    except Exception as ex:
        return {"http": None, "status": "UNREACHABLE", "error_type": type(ex).__name__}
    try:
        body = json.loads(raw)
        if not isinstance(body, dict): raise ValueError("not_json_object")
    except Exception:
        return {"http": status, "status": "INVALID_RESPONSE"}
    return {"http": status, "status": "RECEIVED", "body": body}

def audit(probes, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    superv = probes.get("supervisor", {})
    sup_body = superv.get("body") or {}
    prior_time = sup_body.get("state_updated_at") or sup_body.get("observed_at")
    try:
        age = (now-dt.datetime.fromisoformat(prior_time.replace("Z", "+00:00"))).total_seconds()
    except Exception: age = None
    checks = sup_body.get("checks")
    super_ok = (superv.get("http") == 200 and sup_body.get("status") == "VALIDATED" and sup_body.get("source") == "cron-5m"
                and isinstance(checks, list) and len(checks) >= 4 and all(x.get("ok") is True for x in checks)
                and age is not None and -60 <= age < 900)
    hq = probes.get("hq", {}); hqb = hq.get("body") or {}
    hq_ok = (hq.get("http") == 200 and hqb.get("ok") is True and hqb.get("canonical_company_control") == "UNVERIFIED" and
             (hqb.get("hq_database") or {}).get("reachable") is True and hqb.get("production_authority_migrated") is False)
    recovery = probes.get("recovery", {}); rb = recovery.get("body") or {}
    hold = (recovery.get("http") == 503 and rb.get("decision") == "HOLD_CANONICAL_WORKERS" and rb.get("production_authority_migrated") is False and rb.get("canonical_database_query_responded") is False)
    edge = probes.get("edge", {}); eb = edge.get("body") or {}
    edge_ok = edge.get("http") == 200 and eb.get("ok") is True and eb.get("schema") == "angels.shared-runtime/v1" and eb.get("writes") is False
    octo = probes.get("octopus", {}); ob = octo.get("body") or {}; truth = ob.get("durable_truth") or {}
    octo_no_truth = octo.get("http") == 200 and ob.get("ok") is True and truth.get("available") is False
    aether = probes.get("aether", {}); ab = aether.get("body") or {}
    aether_safe = aether.get("http") == 200 and ab.get("ok") is True and ab.get("event_actions_enabled") is False
    # This is a founder-facing engineering estimate established outside this observer.
    # HTTP 200 must never increment it. Native recovery and real OpenHands are separately verified.
    interventions = []
    if not super_ok: interventions.append("Investigate Cloudflare observer liveness, scope: read-only")
    if not hq_ok: interventions.append("Investigate independent HQ database read-only connectivity")
    if not hold: interventions.append("Check original recovery gate manually: HOLD could not be independently confirmed")
    if not edge_ok: interventions.append("Investigate source Edge health without resuming production")
    if not octo_no_truth: interventions.append("Reassess OCTOPUS durable-truth state manually; do not infer revenue")
    if not aether_safe: interventions.append("Inspect AETHER event-action safety; do not enable external actions")
    interventions.extend(["Verify authorized shell on existing Foundation server before OpenHands installation",
                          "Verify OpenHands process, model access and first independent agent work receipt",
                          "Await provider-supported native PostgreSQL recovery and validate original source data",
                          "Prove cross-provider global single-writer fencing before any production worker effects"])
    return {"schema":"angels.public-readonly-hourly-observer/v1","observed_at_utc":now.isoformat().replace("+00:00", "Z"),
            "cadence":"best-effort hourly cron at minute 7", "engineer_estimate_percent":25,
            "percent_certified":False,"percent_proof":"unchanged founder-facing estimate; no computation from health probes",
            "openhands_running":"NOT_VERIFIED","openhands_workers_started":"NOT_VERIFIED",
            "production_worker_execution":"NOT_CERTIFIED", "original_pg_native_restored":"NOT_VERIFIED",
            "supervisor_live":super_ok,"supervisor_last_state_version":sup_body.get("state_version") if super_ok else None,
            "independent_hq_readonly":hq_ok,"original_production_hold_confirmed":hold,
            "legacy_edge_readonly":edge_ok,"octopus_durable_truth_unavailable":octo_no_truth,
            "aether_events_disabled":aether_safe,"interventions":interventions,"can_dispatch_work":False,
            "authority_granted":False,"no_customer_payment_trade_or_external_effect":True,
            "overall_status":"IN_PROGRESS_NOT_CERTIFIED"}

def markdown(a):
    v=lambda flag: "PASS" if flag else "NOT VERIFIED"
    return (f"### ANGELS — bounded hourly read-only update ({a['observed_at_utc']})\n\n"
            f"**Estimated full mandate progress: ~{a['engineer_estimate_percent']}%** (prior engineering estimate, not freshly certified or automatically increased).\n\n"
            f"| Evidence gate | Result |\n|---|---|\n"
            f"| OpenHands running + ANGELS boys executing | {a['openhands_workers_started']} |\n"
            f"| Original native PostgreSQL restore | {a['original_pg_native_restored']} |\n"
            f"| Canonical worker execution | {a['production_worker_execution']} |\n"
            f"| Cloudflare supervisor fresh | {v(a['supervisor_live'])} |\n"
            f"| Independent HQ read-only | {v(a['independent_hq_readonly'])} |\n"
            f"| Original HOLD gate | {v(a['original_production_hold_confirmed'])} |\n"
            f"| Legacy Edge read-only health | {v(a['legacy_edge_readonly'])} |\n"
            f"| OCTOPUS no durable truth | {v(a['octopus_durable_truth_unavailable'])} |\n"
            f"| AETHER external events disabled | {v(a['aether_events_disabled'])} |\n\n"
            "**Needed interventions (no autonomous production changes):**\n"+
            "".join(f"- {x}\n" for x in a['interventions'])+
            "\nObserver only. No LLM, credentials, company authority, deletion, trading, payments, deployments, or state mutation.\n")

def main():
    probes={k:fetch(k,v) for k,v in ENDPOINTS.items()}
    result=audit(probes)
    output=Path(os.environ.get("ANGELS_OBSERVER_OUTPUT", "."));output.mkdir(parents=True,exist_ok=True)
    (output/"read-only-report.json").write_text(json.dumps(result,indent=2)+"\n", encoding="utf8")
    (output/"read-only-report.md").write_text(markdown(result),encoding="utf8")
    print("ANGELS_30M_READONLY_REPORT="+json.dumps(result,sort_keys=True,separators=(",", ":")))
    # Report without suppressing future runs for provider outages: operator sees fail-closed status.
if __name__=="__main__":main()