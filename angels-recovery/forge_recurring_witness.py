#!/usr/bin/env python3
"""Read-only witness of distinct unattended FORGE schedule cycles, not worker certification.

Fetches GitHub's public API and immutable source receipts. Never executes model
output, handles credentials, grants authority, or writes production state.
"""
import base64
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone

REPO = "visionastro48-dev/shaddow-synthetic-host-gate-20261001"
API = "https://api.github.com/repos/" + REPO
WORKFLOW = "angels-forge-real-local-coding.yml"


def get_json(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ANGELS-FORGE-ReadOnlyRecurrenceWitness/1.0",
    })
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.load(response)


def validate_cycle(run, receipt, source, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        if run["event"] != "schedule" or run["conclusion"] != "success":
            return False, "not_successful_schedule"
        if not (0 <= (now - created).total_seconds() <= 21600):
            return False, "outside_six_hour_window"
        expected = {
            "schema": "angels.forge.durable-acceptance/v1",
            "workflow_event": "schedule",
            "workflow_run_id": run["id"],
            "workflow_source_sha": run["head_sha"],
            "model": "qwen3:4b-instruct",
            "structured_tool_call": True,
            "verified_synthetic_cases": 11,
            "artifacts_sha256_checked": True,
            "no_production_authority": True,
            "gateway_enrolled": False,
            "continuous_workforce_certified": False,
            "issued_github_mission": None,
        }
        for key, value in expected.items():
            if type(receipt.get(key)) is not type(value) or receipt[key] != value:
                return False, "contract_" + key
        if receipt.get("workflow_run_url") != "https://github.com/" + REPO + "/actions/runs/" + str(run["id"]):
            return False, "run_url_mismatch"
        if receipt["source_sha256"] != hashlib.sha256(source).hexdigest():
            return False, "source_hash_mismatch"
        if not isinstance(receipt.get("generation_attempts"), int) or not 1 <= receipt["generation_attempts"] <= 4:
            return False, "invalid_attempts"
        return True, "bounded_schedule_cycle_verified"
    except (KeyError, TypeError, ValueError):
        return False, "malformed_cycle"


def witness(fetch=get_json):
    runs = fetch(API + "/actions/workflows/" + WORKFLOW + "/runs?event=schedule&per_page=10")
    verified, rejected = [], []
    for run in runs.get("workflow_runs", []):
        if run.get("event") != "schedule" or run.get("conclusion") != "success":
            continue
        rid = run["id"]
        root = API + "/contents/angels-recovery/evidence/forge-runs/forge-" + str(rid)
        try:
            record = fetch(root + "/receipt.json")
            source_record = fetch(root + "/gate_verify.py")
            receipt = json.loads(base64.b64decode(record["content"]))
            source = base64.b64decode(source_record["content"])
            valid, reason = validate_cycle(run, receipt, source)
            if valid:
                verified.append(rid)
            else:
                rejected.append({"run_id": rid, "reason": reason})
        except (KeyError, TypeError, ValueError, OSError) as error:
            rejected.append({"run_id": rid, "reason": type(error).__name__})
    return {
        "schema": "angels.forge.readonly-recurrence-witness/v1",
        "verified_unattended_scheduled_cycles": len(set(verified)),
        "verified_run_ids": sorted(set(verified)),
        "rejected": rejected,
        "two_cycle_gate": "PASS_BOUNDED_ONLY" if len(set(verified)) >= 2 else "WAITING",
        "always_on_worker_certified": False,
        "production_authority": False,
        "external_effects_certified": False,
    }


if __name__ == "__main__":
    try:
        result = witness()
        print("ANGELS_FORGE_RECURRENCE_WITNESS=" + json.dumps(result, sort_keys=True), flush=True)
        raise SystemExit(1 if result["rejected"] else 0)
    except Exception as error:
        print("ANGELS_FORGE_RECURRENCE_WITNESS_ERROR=" + type(error).__name__, file=sys.stderr)
        raise SystemExit(2)
