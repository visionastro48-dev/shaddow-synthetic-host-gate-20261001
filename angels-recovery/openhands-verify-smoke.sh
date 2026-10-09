#!/usr/bin/env bash
set -euo pipefail
if ! command -v docker >/dev/null 2>&1; then echo 'NOT_VERIFIED: docker absent'; exit 2; fi
status=$(docker inspect -f '{{.State.Running}}' angels-openhands-isolated 2>/dev/null || echo missing)
if [[ "$status" != true ]]; then echo 'NOT_VERIFIED: OpenHands container not running'; exit 2; fi
# This check is deliberately local to host. A public HTTP port would be unsafe.
if ! curl --fail --silent --show-error --max-time 7 -o /dev/null http://127.0.0.1:8000/; then
  echo 'NOT_VERIFIED: local ingress does not answer'; exit 2
fi
if ss -lnt | grep -E '0\.0\.0\.0:8000|\[::\]:8000' >/dev/null; then
  echo 'BLOCKED: OpenHands management accidentally exposed to public interface'; exit 3
fi
echo 'OPENHANDS_SERVICE_LOCAL_INGRESS_VERIFIED_ONLY; NO MODEL_INFERENCE_OR_AGENT_WORK_PROVEN'