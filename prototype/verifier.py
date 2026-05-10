#!/usr/bin/env python3
"""
Minimal verifier for IDBA and KeyChallenge-style baseline.

Example:
  python3 verifier.py --host 0.0.0.0 --port 9000 --policy idba --difficulty 18 --adapt simple --csv verifier_idba.csv
  python3 verifier.py --host 0.0.0.0 --port 9000 --policy keychallenge --difficulty 18 --adapt fixed --csv verifier_keychallenge.csv
"""

from __future__ import annotations

import argparse
import csv
import socket
import threading
import time
from pathlib import Path
from typing import Set

from idba_common import (
    DEFAULT_SECRET,
    bind_instance_policy,
    new_token,
    now_ns,
    ns_to_ms,
    recv_json_line,
    send_json_line,
    verify_puzzle,
)

LOCK = threading.Lock()
SEEN_TAU: Set[str] = set()
KNOWN_REQUESTERS: Set[str] = set()
RESULTS = []
START_TIME = time.time()


def adapt_difficulty(base: int, requester_id: str, context: str, mode: str, policy: str) -> int:
    if policy == "keychallenge" or mode == "fixed":
        return base

    novelty = 1 if requester_id not in KNOWN_REQUESTERS else 0
    risk = 1 if context in {"committee", "reward", "hotspot"} else 0
    pressure = min(2, int(len(RESULTS) / 100))
    return min(base + novelty + risk + pressure, base + 4)


def handle_client(conn: socket.socket, addr, args) -> None:
    t0 = now_ns()
    status = "error"
    requester_id = "unknown"
    context = "unknown"
    difficulty = args.difficulty
    verify_ms = 0.0
    accepted = False
    fresh = False
    valid = False

    try:
        with conn:
            req = recv_json_line(conn)
            requester_id = str(req.get("requester_id", "unknown"))
            context = str(req.get("context", "default"))

            difficulty = adapt_difficulty(args.difficulty, requester_id, context, args.adapt, args.policy)
            tau = new_token()
            verifier_nonce = new_token()
            instance = bind_instance_policy(
                args.policy,
                args.secret.encode("utf-8"),
                args.verifier_id,
                requester_id,
                tau,
                context,
                difficulty,
                verifier_nonce,
            )

            send_json_line(conn, {
                "type": "challenge",
                "policy": args.policy,
                "verifier_id": args.verifier_id,
                "requester_id": requester_id,
                "context": context,
                "tau": tau,
                "difficulty": difficulty,
                "verifier_nonce": verifier_nonce,
            })

            witness = recv_json_line(conn)
            nonce = int(witness["nonce"])

            vt0 = now_ns()
            with LOCK:
                fresh = tau not in SEEN_TAU
                if fresh:
                    SEEN_TAU.add(tau)

            valid = verify_puzzle(instance, difficulty, nonce)
            verify_ms = ns_to_ms(now_ns() - vt0)

            accepted = bool(fresh and valid)
            status = "accepted" if accepted else "rejected"

            if accepted:
                with LOCK:
                    KNOWN_REQUESTERS.add(requester_id)

            send_json_line(conn, {
                "type": "result",
                "accepted": accepted,
                "fresh": fresh,
                "valid": valid,
                "verify_ms": verify_ms,
                "policy": args.policy,
            })

    except Exception as e:
        status = f"error:{type(e).__name__}"
        try:
            send_json_line(conn, {"type": "result", "accepted": False, "error": str(e), "policy": args.policy})
        except Exception:
            pass

    total_ms = ns_to_ms(now_ns() - t0)
    row = {
        "time_s": f"{time.time() - START_TIME:.6f}",
        "policy": args.policy,
        "client_ip": addr[0],
        "requester_id": requester_id,
        "context": context,
        "difficulty": difficulty,
        "accepted": int(accepted),
        "fresh": int(fresh),
        "valid": int(valid),
        "status": status,
        "verify_ms": f"{verify_ms:.6f}",
        "server_exchange_ms": f"{total_ms:.6f}",
    }

    with LOCK:
        RESULTS.append(row)
        if args.csv:
            write_header = not Path(args.csv).exists()
            with open(args.csv, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                if write_header:
                    writer.writeheader()
                writer.writerow(row)


def reporter(args) -> None:
    while True:
        time.sleep(args.report_interval)
        with LOCK:
            n = len(RESULTS)
            acc = sum(int(r["accepted"]) for r in RESULTS)
            elapsed = max(time.time() - START_TIME, 1e-9)
        print(f"[verifier:{args.policy}] requests={n} accepted={acc} throughput={n/elapsed:.2f} req/s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--policy", choices=["idba", "keychallenge"], default="idba")
    ap.add_argument("--difficulty", type=int, default=18)
    ap.add_argument("--adapt", choices=["fixed", "simple"], default="fixed")
    ap.add_argument("--verifier-id", default="verifier-u")
    ap.add_argument("--secret", default=DEFAULT_SECRET.decode("utf-8"))
    ap.add_argument("--csv", default="verifier_results.csv")
    ap.add_argument("--report-interval", type=float, default=5.0)
    args = ap.parse_args()

    if args.policy == "keychallenge":
        args.adapt = "fixed"

    threading.Thread(target=reporter, args=(args,), daemon=True).start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(512)
    print(
        f"[verifier] listening on {args.host}:{args.port}, policy={args.policy}, "
        f"difficulty={args.difficulty}, adapt={args.adapt}",
        flush=True,
    )

    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr, args), daemon=True).start()


if __name__ == "__main__":
    main()
