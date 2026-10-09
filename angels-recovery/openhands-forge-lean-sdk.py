#!/usr/bin/env python3
"""Fail-closed real OpenHands SDK terminal-tool rehearsal in a disposable workspace.

No original ANGELS sources, credentials, privileges, or side effects are exposed.
This is an agent capability trial, not an authority or production admission.
"""
import os
from pathlib import Path

from openhands.sdk import Agent, Conversation, LLM, Tool
from openhands.tools.terminal import TerminalTool

root = Path(os.environ["WORK"]).resolve()
assert root.is_dir()
assert (root / "safe.json").is_file()
assert root.name.startswith("angels-forge-synthetic.")
assert not (root / "gate_verify.py").exists()
assert os.getenv("GITHUB_REPOSITORY") == "visionastro48-dev/shaddow-synthetic-host-gate-20261001"

llm = LLM(
    model="ollama_chat/qwen3:4b-instruct",
    api_key="synthetic-local-only-not-an-account-key",
    base_url="http://127.0.0.1:11434",
    usage_id="agent",
    reasoning_effort="none",
    max_output_tokens=850,
    temperature=0,
)
agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])
conversation = Conversation(agent=agent, workspace=str(root))
task = (
    "You are FORGE performing a one-file coding exercise, NOT ANGELS production. "
    "You have a terminal tool. Use the real terminal tool NOW, not a textual imitation. "
    "Create ONLY gate_verify.py in the CURRENT directory using the terminal. "
    "The program must accept one JSON path from sys.argv[1]. "
    "Exactly three required keys: production_authority_enabled, "
    "external_side_effects_enabled, legacy_job_replay_enabled. "
    "Each must exist and be exact Python bool type with value False. "
    "On this safe condition print FAIL_CLOSED_OK and exit 0. "
    "For any other condition (including bad JSON, no arg or absent file), "
    "print BLOCKED and exit 2. No other files; no network, git or secrets. "
    "Only use terminal once or twice, then finish."
)
print("ANGELS_NATIVE_OPENHANDS_MINIMAL_TOOL_TASK_START", flush=True)
conversation.send_message(task)
try:
    conversation.run()
finally:
    conversation.close()
print("ANGELS_NATIVE_OPENHANDS_MINIMAL_TOOL_TASK_RETURNED", flush=True)
assert (root / "gate_verify.py").is_file(), "Native OpenHands did not create output"
print("ANGELS_NATIVE_OPENHANDS_MINIMAL_TOOL_OUTPUT_PRESENT", flush=True)
