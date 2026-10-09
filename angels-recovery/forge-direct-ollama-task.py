#!/usr/bin/env python3
"""ANGELS optional direct Ollama tool-call executor inside a disposable agent container.

The company Gateway token stays in a separate supervisor. This process may only
write one bounded file inside its preallocated /workspace/<mission_id> directory.
A 0 exit is never completion: the outside supervisor verifies SHA-256 before ACK.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PREFIX="ANGELS_WORKER_RESULT:"
ALLOWED_MODELS={"qwen3:4b-instruct","qwen2.5:7b","qwen2.5-coder:1.5b"}
ALLOWED_URLS={"http://angels-ollama:11434","http://host.docker.internal:11434"}

def respond(status, detail=""):
    print(PREFIX+json.dumps({"status":status,"detail":str(detail)[:180]},sort_keys=True),flush=True)

def validate_payload(payload, environments=None):
    e=os.environ if environments is None else environments
    if any(key.startswith("ANGELS_GATEWAY_") or key=="ANGELS_MODULE_TOKEN" for key in e):
        raise ValueError("ANGELS_GATEWAY_CREDENTIAL_FORBIDDEN")
    if any(e.get(k) for k in ("OPENROUTER_API_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY")):
        raise ValueError("PAID_OR_REMOTE_MODEL_KEY_FORBIDDEN")
    if not isinstance(payload,dict) or set(payload)!={"mission_id","task","workspace","model","ollama_url","relative_path"}:
        raise ValueError("INVALID_MISSION_PAYLOAD")
    m=payload["mission_id"]
    if not isinstance(m,str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,100}",m):
        raise ValueError("INVALID_MISSION_ID")
    if not isinstance(payload["task"],str) or not 5<=len(payload["task"])<=4000:
        raise ValueError("INVALID_TASK")
    path=payload["relative_path"]
    if not isinstance(path,str) or not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_./-]{0,199}",path):
        raise ValueError("INVALID_RELATIVE_PATH")
    if any(part in ("",".","..") for part in path.split("/")):
        raise ValueError("TRAVERSAL_FORBIDDEN")
    if payload["workspace"]!="/workspace/"+m:
        raise ValueError("FOREIGN_WORKSPACE_FORBIDDEN")
    if payload["model"] not in ALLOWED_MODELS or payload["ollama_url"] not in ALLOWED_URLS:
        raise ValueError("EXTERNAL_MODEL_FORBIDDEN")
    return m,path

def save_generated(root,relative,content):
    if not isinstance(content,str) or not 1<=len(content.encode("utf8"))<=16000:
        raise ValueError("UNTRUSTED_SOURCE_SIZE")
    root=Path(root)
    if not root.is_dir() or root.is_symlink() or root.resolve()!=root:
        raise ValueError("WORKSPACE_MISSING_OR_LINKED")
    parts=relative.split("/")
    dest=root
    for part in parts[:-1]:
        dest=dest/part
        if dest.exists() and dest.is_symlink():raise ValueError("LINKED_WORKSPACE_COMPONENT")
        dest.mkdir(mode=0o700,exist_ok=True)
        if not dest.is_dir() or dest.is_symlink():raise ValueError("INVALID_WORKSPACE_COMPONENT")
    target=dest/parts[-1]
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    descriptor=os.open(str(target),flags,0o600)
    try:
        with os.fdopen(descriptor,"w",encoding="utf8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        try:target.unlink()
        except OSError:pass
        raise
    return target

def call_model(payload,messages):
    schema={"type":"function","function":{
      "name":"write_file",
      "description":"Write the complete bounded source contents to the single authorized mission output file.",
      "parameters":{"type":"object","properties":{
        "filename":{"type":"string","enum":[payload["relative_path"]]},
        "content":{"type":"string","description":"Entire output file content, no markdown fences"}
      },"required":["filename","content"]}}}
    data=json.dumps({
      "model":payload["model"],"messages":messages,"tools":[schema],"stream":False,
      "options":{"temperature":0,"num_ctx":4096,"num_predict":1800}
    }).encode()
    req=urllib.request.Request(payload["ollama_url"]+"/api/chat",data=data,
                               headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=155) as rsp:
        obj=json.load(rsp)
    return obj.get("message") or {}

def run(payload):
    mission_id,rel=validate_payload(payload)
    work=Path(payload["workspace"])
    if not work.is_dir() or work.is_symlink() or work.resolve()!=work:
        raise ValueError("DISPOSABLE_WORKSPACE_UNAVAILABLE")
    messages=[
      {"role":"system","content":("You are a non-production isolated ANGELS coding worker. "
        "Call the actual write_file tool, not textual JSON, to write exactly one file "
        "at the authorized filename. Do not create any additional files, run commands, "
        "send messages, or request credentials. Your work is accepted only by an external hash verifier.")},
      {"role":"user","content":("Write complete contents of "+rel+" for this authorized bounded task:\n"+payload["task"])}
    ]
    for _ in range(2):
        answer=call_model(payload,messages)
        calls=answer.get("tool_calls") or []
        for c in calls:
            function=c.get("function") or {}
            if function.get("name")!="write_file":continue
            arguments=function.get("arguments")
            if isinstance(arguments,str):
                try:arguments=json.loads(arguments)
                except ValueError:arguments=None
            if not isinstance(arguments,dict) or set(arguments)!={"filename","content"} or arguments["filename"]!=rel:
                raise ValueError("INVALID_ACTUAL_TOOL_ARGUMENTS")
            save_generated(work,rel,arguments["content"])
            respond("EXECUTED_UNVERIFIED","real_ollama_structured_tool_call")
            return
        messages.append({"role":"user","content":"Your previous answer was not an ACTUAL write_file tool call. Invoke write_file with the exact authorized filename."})
    raise RuntimeError("NO_REAL_WRITE_FILE_TOOL_CALL")

if __name__=="__main__":
    try:
        run(json.load(sys.stdin))
    except Exception as e:
        respond("FAILED",type(e).__name__+":"+str(e))
        sys.exit(2)
