#!/usr/bin/env python3
"""Verify owner-issued no-authority FORGE mission before issuing GitHub-only ACK.

Consumes trusted GitHub Actions event + committed FORGE receipt AS DATA.
It neither runs model code nor grants ANGELS Gateway or production authority.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

OWNER="visionastro48-dev"
REPO="visionastro48-dev/shaddow-synthetic-host-gate-20261001"
TITLE="ANGELS FORGE TASK: no-authority gate verifier"
MISSION="ANGELS-FORGE-GATE-001"
ROOT="https://github.com/"+REPO


def reject(reason):
    raise ValueError("FORGE_MISSION_ACK_DENIED: "+reason)


def ack(event_path, receipt_path, run_id, attempt, repository, output_path):
    if repository != REPO:
        reject("repository_mismatch")
    if not re.fullmatch(r"[1-9][0-9]{5,19}",str(run_id)):
        reject("invalid_run_id")
    if not re.fullmatch(r"[1-9][0-9]{0,3}",str(attempt)):
        reject("invalid_attempt")
    event=json.loads(pathlib.Path(event_path).read_text())
    issue=event.get("issue")
    if (event.get("action")!="opened" or
        (event.get("repository") or {}).get("full_name")!=REPO or
        not isinstance(issue,dict) or
        (issue.get("user") or {}).get("login")!=OWNER or
        issue.get("title")!=TITLE or
        (issue.get("body") or "").strip()!="mission_id="+MISSION or
        type(issue.get("number")) is not int or issue["number"]<=0):
        reject("untrusted_issue")
    receipt=json.loads(pathlib.Path(receipt_path).read_text())
    mission=receipt.get("issued_github_mission")
    wanted={
        "mission_id":MISSION,
        "github_issue_number":issue["number"],
        "issuer":"github-repository-owner",
        "angels_gateway_authorized":False,
    }
    if not isinstance(mission,dict) or mission!=wanted:
        reject("mission_binding_mismatch")
    checks={
        "schema":"angels.forge.durable-acceptance/v1",
        "workflow_event":"issues",
        "workflow_run_id":int(run_id),
        "workflow_run_url":ROOT+"/actions/runs/"+str(run_id),
        "structured_tool_call":True,
        "verified_synthetic_cases":11,
        "artifacts_sha256_checked":True,
        "no_production_authority":True,
        "gateway_enrolled":False,
        "continuous_workforce_certified":False,
    }
    for key,value in checks.items():
        if type(receipt.get(key)) is not type(value) or receipt[key]!=value:
            reject("receipt_contract_"+key)
    digest=receipt.get("source_sha256")
    if not isinstance(digest,str) or not re.fullmatch(r"[a-f0-9]{64}",digest):
        reject("invalid_source_sha")
    first=receipt.get("workflow_run_attempt")
    if type(first) is not int or not 1<=first<=int(attempt):
        reject("invalid_recorded_attempt")
    marker="ANGELS_FORGE_GITHUB_ACK:run="+str(run_id)+":issue="+str(issue["number"])+":sha256="+digest
    body=(
        "FORGE GitHub mission completed (synthetic, no production authority).\n\n"
        "- Mission: "+MISSION+"\n"
        "- Real AI code generation: verified through recorded structured tool call\n"
        "- Independent model-job checks: 11/11 passed\n"
        "- Source SHA-256: `"+digest+"`\n"
        "- Run: "+ROOT+"/actions/runs/"+str(run_id)+"\n"
        "- Durable receipt: "+ROOT+"/blob/main/angels-recovery/evidence/forge-runs/forge-"+str(run_id)+"/receipt.json\n\n"
        "This ACK is ONLY for the bounded GitHub issue, **not** ANGELS Gateway admission, project approval, or a 24/7 worker certificate.\n\n"
        marker+"\n"
    )
    out=pathlib.Path(output_path)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(body)
    print("FORGE_GITHUB_ISSUE_ACK_READY issue="+str(issue["number"])+" run="+str(run_id)+" marker="+marker)
    return marker


def main():
    parser=argparse.ArgumentParser()
    for arg in ("event","receipt","run-id","run-attempt","repository","output"):
        parser.add_argument("--"+arg,required=True)
    v=parser.parse_args()
    ack(v.event,v.receipt,v.run_id,v.run_attempt,v.repository,v.output)


if __name__=="__main__":
    main()
