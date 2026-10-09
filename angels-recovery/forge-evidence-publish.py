#!/usr/bin/env python3
"""Publish hash-checked, synthetic FORGE acceptance evidence; never execute AI code.

Runs ONLY in the separate GitHub Actions receipt job. No ANGELS runtime tokens.
The model job has contents:read and cannot publish repository state.
"""
import argparse
import hashlib
import json
import re
import stat
from pathlib import Path

REPO = "visionastro48-dev/shaddow-synthetic-host-gate-20261001"
REQUIRED = {"acceptance.json", "gate_verify.py"}


def fail(reason):
    raise ValueError("FORGE_EVIDENCE_REJECTED: " + reason)


def regular_file(path, limit):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size < 1 or info.st_size > limit:
        fail("untrusted_file_type_or_size")
    return path.read_bytes()


def publish(artifact_dir, repo_root, run_id, run_attempt, event, head_sha):
    if not re.fullmatch(r"[1-9][0-9]{5,19}", str(run_id)):
        fail("invalid_run_id")
    if not re.fullmatch(r"[1-9][0-9]{0,3}", str(run_attempt)):
        fail("invalid_attempt")
    if event not in {"push", "schedule", "workflow_dispatch"}:
        fail("unsupported_event")
    if not re.fullmatch(r"[a-f0-9]{40}", str(head_sha)):
        fail("invalid_head_sha")
    artifact_dir = Path(artifact_dir)
    if artifact_dir.is_symlink() or not artifact_dir.is_dir():
        fail("artifact_directory_untrusted")
    if {entry.name for entry in artifact_dir.iterdir()} != REQUIRED:
        fail("artifact_file_set_mismatch")

    source = regular_file(artifact_dir / "gate_verify.py", 9000)
    raw = regular_file(artifact_dir / "acceptance.json", 10000)
    try:
        acceptance = json.loads(raw)
    except (ValueError, UnicodeError):
        fail("malformed_acceptance")
    if not isinstance(acceptance, dict):
        fail("nonobject_acceptance")
    expected = {
        "schema": "angels.forge.real-local-model-coding/v1",
        "outcome": "REAL_MODEL_CODE_ACCEPTED",
        "model": "qwen3:4b-instruct",
        "tool_call_real": True,
        "authority": "none",
        "legacy_data_mounted": False,
        "gateway_enrolled": False,
        "continuous_workforce_certified": False,
    }
    for key, value in expected.items():
        if type(acceptance.get(key)) is not type(value) or acceptance[key] != value:
            fail("acceptance_contract_" + key)
    for key in ("independent_tests_passed", "independent_tests_total"):
        if type(acceptance.get(key)) is not int or acceptance[key] != 11:
            fail("acceptance_tests_" + key)
    if type(acceptance.get("attempts")) is not int or not 1 <= acceptance["attempts"] <= 4:
        fail("attempt_bounds")
    digest = hashlib.sha256(source).hexdigest()
    if acceptance.get("source_sha256") != digest:
        fail("source_digest_mismatch")

    record = {
        "schema": "angels.forge.durable-acceptance/v1",
        "workflow_run_id": int(run_id),
        "workflow_run_attempt": int(run_attempt),
        "workflow_run_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
        "workflow_event": event,
        "workflow_source_sha": head_sha,
        "source_sha256": digest,
        "model": acceptance["model"],
        "generation_attempts": acceptance["attempts"],
        "structured_tool_call": True,
        "verified_synthetic_cases": 11,
        "artifacts_sha256_checked": True,
        "no_production_authority": True,
        "gateway_enrolled": False,
        "continuous_workforce_certified": False,
        "warning": "Source verified as data; source never executed in the privileged receipt-publisher job. No scheduled-cadence or Gateway certification implied.",
    }
    root = Path(repo_root)
    target = root / "angels-recovery" / "evidence" / "forge-runs" / ("forge-" + run_id)
    # GitHub increases RUN_ATTEMPT when a job is retried; preserve the FIRST
    # accepted receipt rather than rewriting it or generating a false conflict.
    # All source, event, scope, and hash fields are still compared below.
    prior_file = target / "receipt.json"
    if prior_file.is_symlink():
        fail("symlink_output")
    if prior_file.exists():
        try:
            previous = json.loads(regular_file(prior_file, 10000))
        except (ValueError, UnicodeError):
            fail("malformed_previous_receipt")
        first_attempt = previous.get("workflow_run_attempt") if isinstance(previous, dict) else None
        if type(first_attempt) is not int or not 1 <= first_attempt <= int(run_attempt):
            fail("invalid_existing_attempt")
        record["workflow_run_attempt"] = first_attempt
    payloads = {
        target / "gate_verify.py": source,
        target / "receipt.json": (json.dumps(record, sort_keys=True, indent=2) + "\n").encode(),
    }
    for output, payload in payloads.items():
        if output.is_symlink():
            fail("symlink_output")
        if output.exists():
            if output.read_bytes() != payload:
                fail("conflicting_replay_" + output.name)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(payload)
    print(f"FORGE_DURABLE_EVIDENCE_ACCEPTED run_id={run_id} sha256={digest} directory={target.relative_to(root)}")
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--sha", required=True)
    opts = parser.parse_args()
    publish(opts.artifact, opts.repo, opts.run_id, opts.attempt, opts.event, opts.sha)


if __name__ == "__main__":
    main()
