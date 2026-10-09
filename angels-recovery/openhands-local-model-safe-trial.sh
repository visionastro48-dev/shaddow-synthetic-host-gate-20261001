#!/usr/bin/env bash
# ANGELS safe, disposable OpenHands CLI test. No company source or secrets are mounted.
set -Eeuo pipefail
umask 077
echo "ANGELS_OPENHANDS_TRIAL_PHASE=START"
test "${GITHUB_REPOSITORY:-}" = "visionastro48-dev/shaddow-synthetic-host-gate-20261001" || { echo "NONAPPROVED_REPO"; exit 2; }
test "${GITHUB_EVENT_NAME:-}" = "push" -o "${GITHUB_EVENT_NAME:-}" = "workflow_dispatch" || exit 2
command -v docker >/dev/null
command -v python3 >/dev/null
test ! -d /srv/angels-foundation-v1 || { echo "NO_PRODUCTION_WORKSPACE_ACCESS"; exit 2; }
export WORK="$(mktemp -d /tmp/angels-forge-synthetic.XXXXXX)"
trap 'sudo docker rm -f angels-ollama-test >/dev/null 2>&1 || true; rm -rf "$WORK"' EXIT
mkdir -p "$WORK";cd "$WORK"
printf '%s\n' '{"production_authority_enabled":false,"external_side_effects_enabled":false,"legacy_job_replay_enabled":false}' > safe.json
sudo docker run --rm -d --name angels-ollama-test -p 127.0.0.1:11434:11434 ollama/ollama:0.11.10 >/dev/null
for i in {1..30};do if curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1;then break;fi;sleep 2;done
curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null
echo "ANGELS_MODEL_DOWNLOAD_START"
timeout 500 sudo docker exec angels-ollama-test ollama pull qwen2.5-coder:3b >/dev/null
echo "ANGELS_MODEL_DOWNLOAD_OK"
python3 - <<'PY'
import json,urllib.request
payload={"model":"qwen2.5-coder:3b","prompt":"Reply only with the text AGENT_READY","stream":False,"options":{"num_predict":12,"temperature":0,"num_ctx":1024}}
request=urllib.request.Request("http://127.0.0.1:11434/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
with urllib.request.urlopen(request,timeout=110) as resp: obj=json.load(resp)
assert obj.get("done") is True and bool((obj.get("response") or "").strip()),"model has not produced inference"
print(json.dumps({"kind":"local_model_inference","verified":True,"model":obj.get("model"),"tokens":obj.get("eval_count")},sort_keys=True))
PY
echo "ANGELS_OPENHANDS_CLI_INSTALL_START"
python3 -m pip -q install --user --break-system-packages 'uv>=0.11.6,<0.13' || python3 -m pip -q install --user 'uv>=0.11.6,<0.13'
export PATH="$HOME/.local/bin:$PATH"
timeout 480 uv tool install openhands --python 3.12 >"$WORK/install.log" 2>&1 || { echo "OPENHANDS_CLI_INSTALL_FAILED";tail -n 14 "$WORK/install.log"|cut -c1-140;exit 3; }
command -v openhands >/dev/null
echo "ANGELS_OPENHANDS_CLI_INSTALLED"
# Generate official default AgentSpec with explicit non-thinking LLM capabilities.
"$HOME/.local/share/uv/tools/openhands/bin/python" - <<'PY'
from openhands.sdk import LLM
from openhands_cli.utils import get_default_cli_agent
from openhands_cli.locations import get_persistence_dir
from pathlib import Path
llm=LLM(model="ollama_chat/qwen2.5-coder:3b",api_key="local-synthetic-model-no-account-key",base_url="http://127.0.0.1:11434",usage_id="agent",reasoning_effort="none")
agent=get_default_cli_agent(llm)
p=Path(get_persistence_dir())/"agent_settings.json"
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(agent.model_dump_json())
verified=__import__("openhands.sdk",fromlist=["Agent"]).Agent.model_validate_json(p.read_text())
assert verified.llm.reasoning_effort=="none"
assert verified.llm.reasoning_effort=="none"
print("ANGELS_OPENHANDS_NONTHINKING_CONFIG_VERIFIED")
PY
export OPENHANDS_SUPPRESS_BANNER=1
export LLM_MODEL='ollama_chat/qwen2.5-coder:3b'
export LLM_API_KEY='local-synthetic-model-no-account-key'
export LLM_BASE_URL='http://127.0.0.1:11434'
export OPENHANDS_MAX_ITERATIONS=12
task="You are a synthetic FORGE-role engineering trial within an EMPTY, DISPOSABLE WORKDIR. This is NOT company production and grants NO authority. Using your coding tools, create only the file gate_verify.py in the present workdir. The Python 3 script must accept a JSON input file path via sys.argv[1], check that production_authority_enabled, external_side_effects_enabled, and legacy_job_replay_enabled are each present and are exactly type bool and False, print FAIL_CLOSED_OK and exit code 0 only for that safe input; for any other condition, missing arguments, invalid JSON or missing file print BLOCKED and exit 2. Do not touch Git, network, credentials, customer data, payments, production, parent directories, or other files. Test the program. Stop after the file is created."
echo "ANGELS_OPENHANDS_REAL_TASK_START"
set +e
timeout 850 openhands --headless --json --override-with-envs --exit-without-confirmation -t "$task" >"$WORK/agent.log" 2>&1
agent_status=$?
set -e
echo "ANGELS_OPENHANDS_AGENT_EXIT=$agent_status"
test -f "$WORK/gate_verify.py" || { echo "AGENT_DID_NOT_CREATE_FILE";grep -E 'LLMBadRequestError|LLMAuthenticationError|LLMError|RuntimeError|ValueError|Traceback|Error:' "$WORK/agent.log" | head -n 6 | cut -c1-1900 || true;exit 4; }
python3 - <<'PY'
import json,pathlib,subprocess,sys,hashlib
root=pathlib.Path.cwd()
source=root/"gate_verify.py"
cases=[
("safe",{"production_authority_enabled":False,"external_side_effects_enabled":False,"legacy_job_replay_enabled":False},0),
("production",{"production_authority_enabled":True,"external_side_effects_enabled":False,"legacy_job_replay_enabled":False},2),
("external",{"production_authority_enabled":False,"external_side_effects_enabled":True,"legacy_job_replay_enabled":False},2),
("replay",{"production_authority_enabled":False,"external_side_effects_enabled":False,"legacy_job_replay_enabled":True},2),
("zero",{"production_authority_enabled":0,"external_side_effects_enabled":False,"legacy_job_replay_enabled":False},2),
("missing",{"production_authority_enabled":False},2),
("null",{"production_authority_enabled":None,"external_side_effects_enabled":False,"legacy_job_replay_enabled":False},2)]
out=[]
for label,body,want in cases:
 f=root/(label+".json");f.write_text(json.dumps(body))
 try:
  p=subprocess.run([sys.executable,str(source),str(f)],text=True,capture_output=True,timeout=10)
  ok=p.returncode==want and (("FAIL_CLOSED_OK" if want==0 else "BLOCKED") in p.stdout)
 except Exception:ok=False
 out.append({"case":label,"pass":ok})
p=subprocess.run([sys.executable,str(source)],text=True,capture_output=True,timeout=10)
out.append({"case":"missing_argument","pass":p.returncode==2 and "BLOCKED" in p.stdout})
print("ANGELS_OPENHANDS_REAL_TASK_RECEIPT="+json.dumps({"schema":"angels.openhands.forge.synthetic-task/v1","real_model_inference":True,"native_openhands_cli_executed":True,"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"passed":sum(x["pass"] for x in out),"total":len(out),"tests":out,"production_authority":False,"legacy_source_mounted":False},sort_keys=True))
if not all(x["pass"] for x in out):sys.exit(6)
PY
echo "ANGELS_OPENHANDS_REAL_TASK_INDEPENDENT_PASS"
