#!/usr/bin/env python3
"""
Shared utilities for the IDBA / KeyChallenge-style TCP prototype.
No third-party Python packages are required.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import time
from typing import Any, Dict, Tuple

DOMAIN = "IDBA-v1"
DEFAULT_SECRET = b"idba-demo-verifier-secret-change-me"


def now_ns() -> int:
    return time.perf_counter_ns()


def ns_to_ms(ns: int) -> float:
    return ns / 1_000_000.0


def canonical_json(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def send_json_line(sock: socket.socket, obj: Dict[str, Any]) -> None:
    sock.sendall(canonical_json(obj) + b"\n")


def recv_json_line(sock: socket.socket, max_bytes: int = 65536) -> Dict[str, Any]:
    chunks = []
    total = 0
    while True:
        b = sock.recv(1)
        if not b:
            raise ConnectionError("socket closed while reading JSON line")
        total += 1
        if total > max_bytes:
            raise ValueError("JSON line too large")
        if b == b"\n":
            break
        chunks.append(b)
    return json.loads(b"".join(chunks).decode("utf-8"))


def bind_instance_policy(
    policy: str,
    secret: bytes,
    verifier_id: str,
    requester_id: str,
    tau: str,
    context: str,
    difficulty: int,
    verifier_nonce: str,
) -> str:
    """
    Policy-aware binding.

    idba:
      binds verifier id, requester id, freshness, context, difficulty, and verifier nonce.

    keychallenge:
      KeyChallenge-style fixed-difficulty key-bound baseline. It binds requester
      identity, freshness, difficulty, and verifier nonce, but intentionally omits
      protected interaction context and verifier-local adaptive state.
    """
    if policy == "idba":
        obj = {
            "domain": DOMAIN,
            "policy": "idba",
            "verifier_id": verifier_id,
            "requester_id": requester_id,
            "tau": tau,
            "context": context,
            "difficulty": difficulty,
            "verifier_nonce": verifier_nonce,
        }
    elif policy == "keychallenge":
        obj = {
            "domain": DOMAIN,
            "policy": "keychallenge",
            "requester_id": requester_id,
            "tau": tau,
            "difficulty": difficulty,
            "verifier_nonce": verifier_nonce,
        }
    else:
        raise ValueError(f"unknown policy: {policy}")

    return hmac.new(secret, canonical_json(obj), hashlib.sha256).hexdigest()


def has_leading_zero_bits(hex_digest: str, difficulty: int) -> bool:
    full_zero_hex = difficulty // 4
    rem_bits = difficulty % 4
    if not hex_digest.startswith("0" * full_zero_hex):
        return False
    if rem_bits == 0:
        return True
    return int(hex_digest[full_zero_hex], 16) < (1 << (4 - rem_bits))


def solve_puzzle(instance_hex: str, difficulty: int, start_nonce: int = 0) -> Tuple[int, int, float]:
    start = now_ns()
    z = start_nonce
    prefix = instance_hex.encode("ascii") + b":"
    while True:
        digest = hashlib.sha256(prefix + str(z).encode("ascii")).hexdigest()
        if has_leading_zero_bits(digest, difficulty):
            return z, z - start_nonce + 1, ns_to_ms(now_ns() - start)
        z += 1


def verify_puzzle(instance_hex: str, difficulty: int, nonce: int) -> bool:
    digest = hashlib.sha256(instance_hex.encode("ascii") + b":" + str(nonce).encode("ascii")).hexdigest()
    return has_leading_zero_bits(digest, difficulty)


def new_token(nbytes: int = 16) -> str:
    return os.urandom(nbytes).hex()


def percentile(values, p: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    frac = k - lo
    return values[lo] * (1 - frac) + values[hi] * frac
