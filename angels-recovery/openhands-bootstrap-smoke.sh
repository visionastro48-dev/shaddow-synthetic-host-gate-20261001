#!/usr/bin/env bash
# ANGELS.co isolated OpenHands candidate. NOT an installer that ran successfully.
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then echo 'BLOCKED: authorized root on existing Foundation host required' >&2; exit 3; fi
if [[ "$(. /etc/os-release && echo "$ID:$VERSION_ID")" != 'ubuntu:24.04' ]]; then echo 'BLOCKED: unverified Ubuntu host' >&2; exit 3; fi
if ! command -v docker >/dev/null; then echo 'BLOCKED: Docker not available. Install Docker via approved host baseline first.' >&2; exit 3; fi
if ! docker info >/dev/null 2>&1; then echo 'BLOCKED: Docker daemon not available' >&2; exit 3; fi
if ! command -v openssl >/dev/null; then echo 'BLOCKED: openssl unavailable' >&2; exit 3; fi
memory=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
if (( memory < 3700000 )); then echo 'BLOCKED: host has less than ~4 GB RAM'; exit 3; fi
base=/srv/angels-foundation-v1
if [[ -e "$base" && ! -d "$base" ]]; then echo 'BLOCKED: existing path not a directory'; exit 3; fi
install -d -m 0700 "$base" "$base/workspaces" "$base/workspaces/isolated-source" "$base/runtime" "$base/secrets" "$base/openhands-home"
keyfile="$base/secrets/agent-canvas.env"
if [[ ! -f "$keyfile" ]]; then
  umask 077
  printf 'LOCAL_BACKEND_API_KEY=%s\n' "$(openssl rand -hex 32)" > "$keyfile"
  chmod 0600 "$keyfile"
fi
if [[ $(stat -c %a "$keyfile") != '600' ]]; then echo 'BLOCKED: bad local key file mode'; exit 3; fi
if docker container inspect angels-openhands-isolated >/dev/null 2>&1; then
  if [[ "$(docker inspect -f '{{.State.Running}}' angels-openhands-isolated)" == true ]]; then
    echo 'OPENHANDS_CONTAINER_EXISTING: verify separately (no assumption of model or agent work)'; exit 0
  fi
  echo 'BLOCKED: existing container name occupied; operator must inspect before restart' >&2; exit 3
fi
# A single stable, preexisting cloud server, no new vendor, only loopback ingress.
# No Docker socket, host root filesystem, or legacy ANGELS production paths mounted.
docker run -d --name angels-openhands-isolated \
  --restart unless-stopped --security-opt no-new-privileges:true \
  --cpus 1.75 --memory 3072m --pids-limit 350 \
  -p 127.0.0.1:8000:8000 \
  --env-file "$keyfile" \
  -v "$base/openhands-home:/home/openhands/.openhands" \
  -v "$base/workspaces:/projects" \
  ghcr.io/openhands/agent-canvas:1.24.0
# Docker success is not model access or worker completion. This file NEVER issues authority.
echo 'START_REQUESTED: check docker state AND authorized health AND a real bounded agent receipt before claiming boys started'