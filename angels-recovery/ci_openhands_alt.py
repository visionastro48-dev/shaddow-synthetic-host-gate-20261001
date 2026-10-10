"""Disposable OpenHands SDK test outside Vercel. Synthetic ONLY: no ANGELS data, secrets or authority."""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

os.environ["OPENHANDS_SUPPRESS_BANNER"] = "1"
os.environ["ALLOW_SHORT_CONTEXT_WINDOWS"] = "true"
from openhands.sdk import Agent, LLM, Conversation
from openhands.tools.terminal import TerminalTool
from openhands.sdk.tool.registry import register_tool
register_tool("TerminalTool", TerminalTool)

for key in ("ANGELS_GATEWAY_URL", "ANGELS_MODULE_TOKEN", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
    if os.environ.get(key):
        raise RuntimeError("FORBIDDEN_SECRET_" + key)

SCENARIOS = (("track_a", "TRACK_A_RECOVERY_LAB_OK"), ("track_b", "TRACK_B_FOUNDATION_LAB_OK"))

def run_task(label, expected, root):
    work = root / label
    work.mkdir()
    llm = LLM(model="ollama_chat/qwen3:4b-instruct",
              base_url="http://127.0.0.1:11434", api_key="local",
              temperature=0, max_input_tokens=8192, max_output_tokens=400,
              timeout=240, num_retries=0, litellm_extra_body={"think": False})
    agent = Agent(llm=llm, tools=[{"name": "TerminalTool", "params": {"terminal_type": "subprocess"}}],
                  include_default_tools=["FinishTool"],
                  system_prompt="You are an isolated, no-secret coding agent. Use terminal tools only inside the disposable workspace. Do not access remote systems or production.")
    conv = Conversation(agent=agent, workspace=str(work), max_iteration_per_run=6,
                        visualizer=None, persistence_dir=str(root / (label + "-receipts")),
                        callbacks=[lambda e: print("SDK_EVENT", label, type(e).__name__, flush=True)])
    try:
        print("SDK_TASK_START", label, flush=True)
        conv.send_message("Create proof.sh in the workspace containing exactly two lines: #!/usr/bin/env bash and echo " + expected + ". Run bash proof.sh using the terminal tool, observe the output, and finish.")
        conv.run()
    finally:
        conv.close()
    target = work / "proof.sh"
    if not target.is_file() or target.read_text().strip() != "#!/usr/bin/env bash\necho " + expected:
        raise RuntimeError(label + "_SOURCE_NOT_ACCEPTED")
    proc = subprocess.run(["bash", str(target)], cwd=work, capture_output=True, text=True, timeout=10)
    if proc.returncode != 0 or proc.stdout.strip() != expected:
        raise RuntimeError(label + "_INDEPENDENT_TEST_FAILED")
    receipt = {"scenario": label, "verified": True, "stdout": proc.stdout.strip(),
               "source_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
               "original_angel_enrolled": False, "production_authority": False,
               "track_done": False, "permanent_runtime": False}
    print("SDK_ACCEPTANCE", json.dumps(receipt, sort_keys=True), flush=True)

with tempfile.TemporaryDirectory(prefix="angels-openhands-public-test-") as tmp:
    for name, line in SCENARIOS:
        run_task(name, line, Path(tmp))
print("OPENHANDS_TWO_DISPOSABLE_TASKS_ACCEPTED", flush=True)
