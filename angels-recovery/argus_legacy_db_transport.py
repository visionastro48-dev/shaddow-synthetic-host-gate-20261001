#!/usr/bin/env python3
"""ANGELS ARGUS read-only, credential-free legacy Postgres transport witness.

A TCP connect is not SQL authentication, data recovery, authority or a health
certificate. This script has no write path, no optional target argument and no
credentials. It runs inside ANGELS's existing read-only scheduled observer.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import socket
from datetime import datetime, timezone

TARGET = "db.yztkpjvkpqdfhltjqbzx.supabase.co"
PORT = 5432
TIMEOUT_SECONDS = 2.0
MAX_ADDRESSES = 4


def check_tcp_transport():
    try:
        destinations = socket.getaddrinfo(TARGET, PORT, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return "DNS_FAILED", 0
    tried = 0
    failed = []
    for family, socktype, protocol, _name, address in destinations:
        if tried >= MAX_ADDRESSES:
            break
        tried += 1
        try:
            with socket.socket(family, socktype, protocol) as connection:
                connection.settimeout(TIMEOUT_SECONDS)
                connection.connect(address)
            return "TCP_REACHABLE", tried
        except ConnectionRefusedError:
            failed.append("TCP_REFUSED")
        except (TimeoutError, socket.timeout):
            failed.append("TCP_TIMEOUT")
        except OSError as exc:
            failed.append("NETWORK_UNREACHABLE" if exc.errno in
                          (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EADDRNOTAVAIL)
                          else "TCP_OTHER_ERROR")
    if not tried:
        return "NO_RESOLVED_ADDRESS", 0
    if "TCP_REFUSED" in failed:
        return "TCP_REFUSED", tried
    if "TCP_TIMEOUT" in failed:
        return "TCP_TIMEOUT", tried
    if "NETWORK_UNREACHABLE" in failed:
        return "NETWORK_UNREACHABLE", tried
    return "TCP_OTHER_ERROR", tried


def build_receipt(status, attempts):
    if status not in {"DNS_FAILED", "TCP_REACHABLE", "TCP_REFUSED", "TCP_TIMEOUT",
                      "NETWORK_UNREACHABLE", "NO_RESOLVED_ADDRESS", "TCP_OTHER_ERROR"}:
        raise ValueError("unknown_transport_status")
    if not isinstance(attempts, int) or not 0 <= attempts <= MAX_ADDRESSES:
        raise ValueError("invalid_attempt_count")
    receipt = {
        "schema": "angels.argus-legacy-db-transport/v1",
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "target": "legacy-supabase-postgresql",
        "port": PORT,
        "operation_class": "READ_ONLY_TCP_CONNECT",
        "status": status,
        "address_attempts": attempts,
        "credentials_used": False,
        "sql_query_performed": False,
        "database_health_certified": False,
        "foundation_authority_formed": False,
        "external_side_effects": False,
        "canonical_workers_resumed": False,
    }
    canonical = json.dumps(receipt, separators=(",", ":"), sort_keys=True)
    receipt["receipt_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt


def main():
    state, attempts = check_tcp_transport()
    receipt = build_receipt(state, attempts)
    print("ANGELS_ARGUS_LEGACY_DB_TRANSPORT=" + json.dumps(receipt, sort_keys=True), flush=True)
    print("ANGELS_ARGUS_LEGACY_DB_TRANSPORT=OBSERVED_NOT_AUTHORIZED", flush=True)
    # Expected closed transport is an observation, not a failed GitHub workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
