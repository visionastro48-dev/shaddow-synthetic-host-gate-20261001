#!/usr/bin/env python3
"""ANGELS FORGE: disposable, no-authority LOCAL model coding crucible.

This uses only Ollama's real structured tool-call API (no mocked LLM output).
No private repository, account key, Gateway authority or paid model is involved.
It is NOT original ANGELS agent enrollment and does not promote source.
"""
import ast, hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

MODEL="qwen3:4b-instruct"
ENDPOINT="http://127.0.0.1:11434/api/chat"
MAX_ATTEMPTS=1
CONTRACT={"mission_id":"FORGE-LEASE-002","writer_id":"foundation-worker-1",
          "claim_epoch":7,"external_effects_allowed":False,"nonce":"0123456789abcdef"}
TASK=(
 "Write exactly one Python 3 script lease_verify.py. It takes exactly ONE JSON filename. "
 "Return exit 0 and print CLAIM_OK ONLY when JSON is a dictionary with EXACTLY these five keys: "
 "mission_id, writer_id, claim_epoch, external_effects_allowed, nonce. "
 "mission_id must be string FORGE-LEASE-002; writer_id must be string foundation-worker-1. "
 "claim_epoch must have EXACT Python type int within range 1..9999 inclusive, never bool. "
 "external_effects_allowed must be exact bool False. nonce must be exactly 16 lowercase hexadecimal "
 "characters (no uppercase), using only characters 0123456789abcdef. "
 "Any invalid/missing/extra key, wrong type/value, malformed/nonexistent JSON, missing or extra "
 "command argument MUST print BLOCKED and exit 2. "
 "Use ONLY json and sys imports, do not write files or use dynamic imports. "
 "Use exact set(data.keys()) equality to reject unexpected keys. "
 "Write full source through a REAL write_lease_code tool call; no textual imitation."
)
TOOL={"type":"function","function":{
 "name":"write_lease_code",
 "description":"Write one Python gate_verifier source file inside a disposable workspace.",
 "parameters":{"type":"object","properties":{
    "filename":{"type":"string","enum":["lease_verify.py"]},
    "content":{"type":"string","description":"Entire actual Python program source"}
  },"required":["filename","content"]}}}

def emit(event, **data):
 print(json.dumps({"event":event,"at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),**data},sort_keys=True),flush=True)

def llm(messages):
 request=urllib.request.Request(ENDPOINT,
  data=json.dumps({"model":MODEL,"messages":messages,"tools":[TOOL],"stream":False,
                   "options":{"num_ctx":8192,"num_predict":1800,"temperature":0}}).encode(),
  headers={"content-type":"application/json"},method="POST")
 with urllib.request.urlopen(request,timeout=170) as response:
  obj=json.load(response)
 if not isinstance(obj.get("message"),dict): raise RuntimeError("INVALID_MODEL_RESPONSE")
 return obj["message"]

def scan_code(content):
 if not isinstance(content,str) or not 80<=len(content)<=9000:
  raise ValueError("SOURCE_SIZE_OUT_OF_BOUNDS")
 tree=ast.parse(content,filename="lease_verify.py")
 forbidden={"eval","exec","compile","__import__","input","breakpoint"}
 for node in ast.walk(tree):
  if isinstance(node,(ast.Import,ast.ImportFrom)):
   if not isinstance(node,ast.Import) or any(alias.name not in {"json","sys"} for alias in node.names):
    raise ValueError("UNAUTHORIZED_IMPORT")
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in forbidden:
   raise ValueError("UNAUTHORIZED_EXECUTION_PRIMITIVE")
  if isinstance(node,(ast.Global,ast.Nonlocal)):
   raise ValueError("UNEXPECTED_GLOBAL_STATE")

def assess(file,root):
 cases=[
  ("valid",CONTRACT,0),
  ("epoch_zero",{**CONTRACT,"claim_epoch":0},2),
  ("epoch_negative",{**CONTRACT,"claim_epoch":-1},2),
  ("epoch_bool",{**CONTRACT,"claim_epoch":True},2),
  ("epoch_string",{**CONTRACT,"claim_epoch":"7"},2),
  ("epoch_over",{**CONTRACT,"claim_epoch":10000},2),
  ("writer_wrong",{**CONTRACT,"writer_id":"other-worker"},2),
  ("mission_wrong",{**CONTRACT,"mission_id":"FORGE-LEASE-001"},2),
  ("external_effect",{**CONTRACT,"external_effects_allowed":True},2),
  ("nonce_short",{**CONTRACT,"nonce":"abc"},2),
  ("nonce_upper",{**CONTRACT,"nonce":"0123456789abcdeF"},2),
  ("nonce_nonhex",{**CONTRACT,"nonce":"0123456789abcdeg"},2),
  ("extra",{**CONTRACT,"unexpected":False},2),
  ("missing",{"writer_id":"foundation-worker-1"},2),
  ("null",{**CONTRACT,"nonce":None},2),
 ]
 problems=[]
 for label,data,want in cases:
  inp=root/(label+".json");inp.write_text(json.dumps(data))
  try:
   proc=subprocess.run([sys.executable,"-I",str(file),str(inp)],cwd=root,capture_output=True,text=True,timeout=8,
        env={"PATH":os.environ.get("PATH","/usr/bin:/bin")})
   if proc.returncode!=want or proc.stdout.strip()!=("CLAIM_OK" if want==0 else "BLOCKED"):
    problems.append(label+": rc="+str(proc.returncode)+" stdout="+repr(proc.stdout[:80])+" stderr="+repr(proc.stderr[:80]))
  except Exception as exc:problems.append(label+":"+type(exc).__name__)
 for label,args in [("no_arg",[]),("nonexistent",[str(root/"missing.json")]),("extra_arg",[str(root/"valid.json"),"EXTRA"])]:
  try:
   proc=subprocess.run([sys.executable,"-I",str(file),*args],cwd=root,capture_output=True,text=True,timeout=8,
        env={"PATH":os.environ.get("PATH","/usr/bin:/bin")})
   if proc.returncode!=2 or proc.stdout.strip()!="BLOCKED":problems.append(label+": rc="+str(proc.returncode))
  except Exception as exc:problems.append(label+":"+type(exc).__name__)
 return len(cases)+3-len(problems),len(cases)+3,problems

def issued_mission():
 """Accept ONLY one explicit bounded owner-issued GitHub issue; never arbitrary issue prompts."""
 if os.environ.get("GITHUB_EVENT_NAME") != "issues":
  return None
 event_file = os.environ.get("GITHUB_EVENT_PATH")
 if not event_file: raise RuntimeError("MISSING_SIGNED_GITHUB_EVENT")
 data=json.loads(Path(event_file).read_text())
 issue=data.get("issue") or {}
 if (data.get("action")!="opened" or
     (data.get("repository") or {}).get("full_name")!="visionastro48-dev/shaddow-synthetic-host-gate-20261001" or
     (issue.get("user") or {}).get("login")!="visionastro48-dev" or
     issue.get("title")!="ANGELS FORGE TASK: no-authority gate verifier" or
     (issue.get("body") or "").strip()!="mission_id=ANGELS-FORGE-GATE-001" or
     type(issue.get("number")) is not int):
  raise RuntimeError("MISSION_NOT_AUTHORIZED_FOR_SYNTHETIC_CARRIER")
 return {"mission_id":"ANGELS-FORGE-GATE-001",
         "github_issue_number":issue["number"],
         "issuer":"github-repository-owner",
         "angels_gateway_authorized":False}

def main():
 if os.environ.get("GITHUB_REPOSITORY")!="visionastro48-dev/shaddow-synthetic-host-gate-20261001":
  raise RuntimeError("UNAUTHORIZED_REPOSITORY")
 for secret in ("ANGELS_GATEWAY_URL","ANGELS_MODULE_TOKEN","OPENROUTER_API_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY"):
  if os.environ.get(secret):raise RuntimeError("FORBIDDEN_SECRET_IN_SYNTHETIC_RUNNER")
 mission=issued_mission()
 if mission: emit("BOUNDED_OWNER_ISSUED_MISSION_ACCEPTED",**mission)
 with tempfile.TemporaryDirectory(prefix="angels-forge-model-") as tmp:
  root=Path(tmp).resolve()
  history=[
   {"role":"system","content":"You are FORGE, a bounded coding agent in a disposable, no-secrets workspace. The only way to write a file is to CALL the real write_lease_code tool. Do not output a textual imitation of a tool call. Provide complete source in the content argument. No external services or rights."},
   {"role":"user","content":TASK}
  ]
  for attempt in range(1,MAX_ATTEMPTS+1):
   message=llm(history)
   calls=message.get("tool_calls") or []
   tool=next((c for c in calls if c.get("function",{}).get("name")=="write_lease_code"),None)
   if not tool:
    emit("MODEL_NO_REAL_TOOL_CALL",attempt=attempt)
    history.append({"role":"assistant","content":(message.get("content") or "")[:1500]})
    history.append({"role":"user","content":"You DID NOT invoke the actual write_lease_code tool. MUST call that tool with filename lease_verify.py and complete correct source. Not text."})
    continue
   fields=tool.get("function",{}).get("arguments")
   if isinstance(fields,str):
    try:fields=json.loads(fields)
    except ValueError:fields={}
   if not isinstance(fields,dict) or set(fields)!={"filename","content"} or fields["filename"]!="lease_verify.py":
    emit("INVALID_REAL_TOOL_ARGUMENTS",attempt=attempt)
    history.append({"role":"user","content":"Your tool arguments were invalid. Call write_lease_code with exactly filename and content."})
    continue
   content=fields["content"]
   try:
    scan_code(content)
   except Exception as exc:
    emit("SOURCE_REJECTED_BY_STATIC_GATE",attempt=attempt,reason=type(exc).__name__+":"+str(exc)[:100])
    history.append({"role":"user","content":"Your source failed the static security check: "+str(exc)+". Repair by calling write_lease_code."})
    continue
   target=root/"lease_verify.py"
   target.write_text(content)
   passed,total,problems=assess(target,root)
   emit("REAL_AGENT_CODING_ATTEMPT",attempt=attempt,structured_tool_call=True,
        source_sha256=hashlib.sha256(content.encode()).hexdigest(),tests_passed=passed,tests_total=total,
        failing_cases=problems)
   if not problems:
    receipt={"schema":"angels.forge.second-bounded-coding/v1",
             "outcome":"REAL_MODEL_CODE_ACCEPTED","model":MODEL,"attempts":attempt,
             "tool_call_real":True,"source_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
             "independent_tests_passed":total,"independent_tests_total":total,
             "authority":"none","legacy_data_mounted":False,"gateway_enrolled":False,
             "continuous_workforce_certified":False}
    if mission:receipt["issued_github_mission"]=mission
    # Retain only synthetic, independently verified output outside the disposable workdir.
    export = Path(os.environ.get("GITHUB_WORKSPACE", str(root))) / "forge-lease-output"
    export.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copyfile(target, export / "lease_verify.py")
    (export / "acceptance.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    copied_hash=hashlib.sha256((export / "lease_verify.py").read_bytes()).hexdigest()
    if copied_hash!=receipt["source_sha256"]:raise RuntimeError("TRANSFER_ARTIFACT_DIGEST_CHANGED")
    print("ANGELS_FORGE_SECOND_CODING_RECEIPT="+json.dumps(receipt,sort_keys=True),flush=True)
    return
   history=[
    {"role":"system","content":"You are a coding repair agent. You must call the actual write_lease_code tool. No textual imitation."},
    {"role":"user","content":TASK+"\nYour previous attempt failed these independent tests: "+json.dumps(problems[:7])+"\nRevalidate all 18 cases including unexpected keys, bool epoch, invalid nonce, and extra arguments. The only valid keys are mission_id, writer_id, claim_epoch, external_effects_allowed, nonce. Source was:\n"+content[:3500]+"\nCall write_lease_code again with repaired full source."}
   ]
 emit("SECOND_MISSION_REJECTED_SOURCE_DIAGNOSTIC", candidate_source=content[:6000], failing_cases=problems, attempt=attempt)
 raise RuntimeError("REAL_AGENT_COULD_NOT_PASS_INDEPENDENT_TESTS")

if __name__=="__main__":
 try: main()
 except Exception as exc:
  emit("FORGE_FAILED",reason=type(exc).__name__+":"+str(exc)[:180])
  sys.exit(2)
