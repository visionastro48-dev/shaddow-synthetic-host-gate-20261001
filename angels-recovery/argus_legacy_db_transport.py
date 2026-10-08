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


def check_tcp_transport(*, with_details=False):
    """Observe at most four direct endpoint addresses; never authenticate.

    The opt-in family summary exposes IPv4/IPv6 transport compatibility
    without revealing resolved addresses. Default tuple remains v1-compatible.
    """
    def response(status, tried, families):
        return (status, tried, families) if with_details else (status, tried)
    try:
        destinations = socket.getaddrinfo(TARGET, PORT, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return response("DNS_FAILED", 0, [])
    tried = 0
    failed = []
    families = []
    for family, socktype, protocol, _name, address in destinations:
        if tried >= MAX_ADDRESSES:
            break
        tried += 1
        family_label = "IPv6" if family == socket.AF_INET6 else "IPv4" if family == socket.AF_INET else "OTHER"
        if family_label not in families:
            families.append(family_label)
        try:
            with socket.socket(family, socktype, protocol) as connection:
                connection.settimeout(TIMEOUT_SECONDS)
                connection.connect(address)
            return response("TCP_REACHABLE", tried, families)
        except ConnectionRefusedError:
            failed.append("TCP_REFUSED")
        except (TimeoutError, socket.timeout):
            failed.append("TCP_TIMEOUT")
        except OSError as exc:
            failed.append("NETWORK_UNREACHABLE" if exc.errno in
                          (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EADDRNOTAVAIL)
                          else "TCP_OTHER_ERROR")
    if not tried:
        return response("NO_RESOLVED_ADDRESS", 0, families)
    if "TCP_REFUSED" in failed:
        return response("TCP_REFUSED", tried, families)
    if "TCP_TIMEOUT" in failed:
        return response("TCP_TIMEOUT", tried, families)
    if "NETWORK_UNREACHABLE" in failed:
        return response("NETWORK_UNREACHABLE", tried, families)
    return response("TCP_OTHER_ERROR", tried, families)


def build_receipt(status, attempts, observed_families=None):
    if status not in {"DNS_FAILED", "TCP_REACHABLE", "TCP_REFUSED", "TCP_TIMEOUT",
                      "NETWORK_UNREACHABLE", "NO_RESOLVED_ADDRESS", "TCP_OTHER_ERROR"}:
        raise ValueError("unknown_transport_status")
    if not isinstance(attempts, int) or not 0 <= attempts <= MAX_ADDRESSES:
        raise ValueError("invalid_attempt_count")
    if observed_families is None:
        observed_families = []
    if not isinstance(observed_families, list) or len(observed_families) > 3 or any(
            f not in ("IPv4", "IPv6", "OTHER") for f in observed_families) or len(set(observed_families)) != len(observed_families):
        raise ValueError("invalid_dns_family_summary")
    receipt = {
        "schema": "angels.argus-legacy-db-transport/v1",
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "target": "legacy-supabase-postgresql",
        "port": PORT,
        "operation_class": "READ_ONLY_TCP_CONNECT",
        "status": status,
        "address_attempts": attempts,
        "observed_address_families": observed_families,
        "network_scope": "GITHUB_ACTIONS_RUNNER_ONLY",
        "direct_ipv6_route_limitation_possible": (
            status == "NETWORK_UNREACHABLE" and observed_families == ["IPv6"]),
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
    state, attempts, families = check_tcp_transport(with_details=True)
    receipt = build_receipt(state, attempts, families)
    print("ANGELS_ARGUS_LEGACY_DB_TRANSPORT=" + json.dumps(receipt, sort_keys=True), flush=True)
    print("ANGELS_ARGUS_LEGACY_DB_TRANSPORT=OBSERVED_NOT_AUTHORIZED", flush=True)
    # Expected closed transport is an observation, not a failed GitHub workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
