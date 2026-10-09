#!/usr/bin/env python3
"""ANGELS FORGE: disposable, no-authority LOCAL model coding crucible.

This uses only Ollama's real structured tool-call API (no mocked LLM output).
No private repository, account key, Gateway authority or paid model is involved.
It is NOT original ANGELS agent enrollment and does not promote source.
"""
import ast, hashlib, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

MODEL="qwen3:4b-instruct"
ENDPOINT="http://127.0.0.1:11434/api/chat"
MAX_ATTEMPTS=4
CONTRACT={
 "production_authority_enabled":False,
 "external_side_effects_enabled":False,
 "legacy_job_replay_enabled":False,
}
TASK=(
 "Create one Python 3 script gate_verify.py. It must accept exactly one JSON filename "
 "argument, read JSON from that path, and return exit 0 with stdout FAIL_CLOSED_OK "
 "ONLY if JSON is a dictionary with EXACTLY these three keys: "
 "production_authority_enabled, external_side_effects_enabled, legacy_job_replay_enabled; "
 "each corresponding value must have exact Python type bool and value False. "
 "For every other case (missing file, invalid JSON, argument missing, unexpected key, "
 "missing key, null, 0/1 instead of bool, True), stdout BLOCKED, exit status 2. "
 "Write straightforward code using ONLY the json and sys Python standard modules. "
 "Never use other imports or filesystem writes; only the requested gate_verify.py."
)
TOOL={"type":"function","function":{
 "name":"write_gate_code",
 "description":"Write one Python gate_verifier source file inside a disposable workspace.",
 "parameters":{"type":"object","properties":{
    "filename":{"type":"string","enum":["gate_verify.py"]},
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
 tree=ast.parse(content,filename="gate_verify.py")
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
 ("safe",CONTRACT,0),("production",{**CONTRACT,"production_authority_enabled":True},2),
 ("external",{**CONTRACT,"external_side_effects_enabled":True},2),
 ("replay",{**CONTRACT,"legacy_job_replay_enabled":True},2),
 ("integer",{**CONTRACT,"production_authority_enabled":0},2),
 ("missing",{"production_authority_enabled":False},2),
 ("null",{**CONTRACT,"external_side_effects_enabled":None},2),
 ("unexpected",{**CONTRACT,"unexpected":1},2),
 ("string",{**CONTRACT,"legacy_job_replay_enabled":"false"},2)
 ]
 problems=[]
 for label,data,want in cases:
  inp=root/(label+".json");inp.write_text(json.dumps(data))
  try:
   run=subprocess.run([sys.executable,"-I",str(file),str(inp)],cwd=root,
                      capture_output=True,text=True,timeout=8,
                      env={"PATH":os.environ.get("PATH","/usr/bin:/bin")})
   if run.returncode!=want or run.stdout.strip()!=("FAIL_CLOSED_OK" if want==0 else "BLOCKED"):
    problems.append(label+": rc="+str(run.returncode)+" stdout="+repr(run.stdout[:80])+" stderr="+repr(run.stderr[:80]))
  except Exception as exc: problems.append(label+":"+type(exc).__name__)
 for label,args in [("no_arg",[]),("nonexistent",[str(root/"missing.json")])]:
  try:
   p=subprocess.run([sys.executable,"-I",str(file),*args],cwd=root,capture_output=True,text=True,timeout=8,
                    env={"PATH":os.environ.get("PATH","/usr/bin:/bin")})
   if p.returncode!=2 or p.stdout.strip()!="BLOCKED":problems.append(label+": rc="+str(p.returncode))
  except Exception as exc:problems.append(label+":"+type(exc).__name__)
 return len(cases)+2-len(problems),len(cases)+2,problems

def main():
 if os.environ.get("GITHUB_REPOSITORY")!="visionastro48-dev/shaddow-synthetic-host-gate-20261001":
  raise RuntimeError("UNAUTHORIZED_REPOSITORY")
 for secret in ("ANGELS_GATEWAY_URL","ANGELS_MODULE_TOKEN","OPENROUTER_API_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY"):
  if os.environ.get(secret):raise RuntimeError("FORBIDDEN_SECRET_IN_SYNTHETIC_RUNNER")
 with tempfile.TemporaryDirectory(prefix="angels-forge-model-") as tmp:
  root=Path(tmp).resolve()
  history=[
   {"role":"system","content":"You are FORGE, a bounded coding agent in a disposable, no-secrets workspace. The only way to write a file is to CALL the real write_gate_code tool. Do not output a textual imitation of a tool call. Provide complete source in the content argument. No external services or rights."},
   {"role":"user","content":TASK}
  ]
  for attempt in range(1,MAX_ATTEMPTS+1):
   message=llm(history)
   calls=message.get("tool_calls") or []
   tool=next((c for c in calls if c.get("function",{}).get("name")=="write_gate_code"),None)
   if not tool:
    emit("MODEL_NO_REAL_TOOL_CALL",attempt=attempt)
    history.append({"role":"assistant","content":(message.get("content") or "")[:1500]})
    history.append({"role":"user","content":"You DID NOT invoke the actual write_gate_code tool. MUST call that tool with filename gate_verify.py and complete correct source. Not text."})
    continue
   fields=tool.get("function",{}).get("arguments")
   if isinstance(fields,str):
    try:fields=json.loads(fields)
    except ValueError:fields={}
   if not isinstance(fields,dict) or set(fields)!={"filename","content"} or fields["filename"]!="gate_verify.py":
    emit("INVALID_REAL_TOOL_ARGUMENTS",attempt=attempt)
    history.append({"role":"user","content":"Your tool arguments were invalid. Call write_gate_code with exactly filename and content."})
    continue
   content=fields["content"]
   try:
    scan_code(content)
   except Exception as exc:
    emit("SOURCE_REJECTED_BY_STATIC_GATE",attempt=attempt,reason=type(exc).__name__+":"+str(exc)[:100])
    history.append({"role":"user","content":"Your source failed the static security check: "+str(exc)+". Repair by calling write_gate_code."})
    continue
   target=root/"gate_verify.py"
   target.write_text(content)
   passed,total,problems=assess(target,root)
   emit("REAL_AGENT_CODING_ATTEMPT",attempt=attempt,structured_tool_call=True,
        source_sha256=hashlib.sha256(content.encode()).hexdigest(),tests_passed=passed,tests_total=total,
        failing_cases=problems)
   if not problems:
    receipt={"schema":"angels.forge.real-local-model-coding/v1",
             "outcome":"REAL_MODEL_CODE_ACCEPTED","model":MODEL,"attempts":attempt,
             "tool_call_real":True,"source_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
             "independent_tests_passed":total,"independent_tests_total":total,
             "authority":"none","legacy_data_mounted":False,"gateway_enrolled":False,
             "continuous_workforce_certified":False}
    print("ANGELS_FORGE_REAL_CODING_RECEIPT="+json.dumps(receipt,sort_keys=True),flush=True)
    return
   history=[
    {"role":"system","content":"You are a coding repair agent. You must call the actual write_gate_code tool. No textual imitation."},
    {"role":"user","content":TASK+"\nYour previous attempt failed these independent tests: "+json.dumps(problems[:7])+"\nSource was:\n"+content[:3500]+"\nCall write_gate_code again with repaired full source."}
   ]
 raise RuntimeError("REAL_AGENT_COULD_NOT_PASS_INDEPENDENT_TESTS")

if __name__=="__main__":
 try: main()
 except Exception as exc:
  emit("FORGE_FAILED",reason=type(exc).__name__+":"+str(exc)[:180])
  sys.exit(2)
