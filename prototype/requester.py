#!/usr/bin/env python3
"""
Minimal requester/client for IDBA and KeyChallenge-style baseline.
"""

from __future__ import annotations

import argparse
import csv
import random
import socket
import time
from pathlib import Path
from typing import Dict, List

from idba_common import (
    DEFAULT_SECRET,
    bind_instance_policy,
    ns_to_ms,
    now_ns,
    percentile,
    recv_json_line,
    send_json_line,
    solve_puzzle,
)


def one_request(args, requester_id: str, context: str) -> Dict[str, object]:
    t0 = now_ns()
    challenge_rtt_ms = float("nan")
    result_rtt_ms = float("nan")
    solve_ms = float("nan")
    hashes = 0
    accepted = False
    difficulty = -1
    policy = "unknown"
    status = "error"
    verify_ms = float("nan")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(args.timeout)
        sock.connect((args.server, args.port))

        send_json_line(sock, {
            "type": "request",
            "requester_id": requester_id,
            "context": context,
            "role": args.role,
            "sent_ns": t0,
        })

        t_ch0 = now_ns()
        ch = recv_json_line(sock)
        challenge_rtt_ms = ns_to_ms(now_ns() - t_ch0)

        policy = str(ch.get("policy", "idba"))
        difficulty = int(ch["difficulty"])
        instance = bind_instance_policy(
            policy,
            args.secret.encode("utf-8"),
            ch["verifier_id"],
            requester_id,
            ch["tau"],
            context,
            difficulty,
            ch["verifier_nonce"],
        )

        nonce, hashes, solve_ms = solve_puzzle(instance, difficulty)
        send_json_line(sock, {
            "type": "witness",
            "requester_id": requester_id,
            "nonce": nonce,
            "hashes": hashes,
            "client_solve_ms": solve_ms,
        })

        t_res0 = now_ns()
        res = recv_json_line(sock)
        result_rtt_ms = ns_to_ms(now_ns() - t_res0)
        accepted = bool(res.get("accepted", False))
        status = "accepted" if accepted else "rejected"
        verify_ms = float(res.get("verify_ms", "nan"))
        sock.close()

    except Exception as e:
        status = f"error:{type(e).__name__}"

    total_ms = ns_to_ms(now_ns() - t0)
    return {
        "policy": policy,
        "requester_id": requester_id,
        "context": context,
        "difficulty": difficulty,
        "accepted": int(accepted),
        "status": status,
        "challenge_rtt_ms": f"{challenge_rtt_ms:.6f}",
        "result_rtt_ms": f"{result_rtt_ms:.6f}",
        "solve_ms": f"{solve_ms:.6f}",
        "verify_ms": f"{verify_ms:.6f}",
        "hashes": hashes,
        "total_exchange_ms": f"{total_ms:.6f}",
    }


def write_row(csv_path: str, row: Dict[str, object]) -> None:
    write_header = not Path(csv_path).exists()
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--role", choices=["honest", "attacker"], default="honest")
    ap.add_argument("--requests", type=int, default=100)
    ap.add_argument("--identities", type=int, default=1)
    ap.add_argument("--rate", type=float, default=5.0)
    ap.add_argument("--difficulty-context", default="default")
    ap.add_argument("--contexts", default="default,committee,reward,hotspot")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--secret", default=DEFAULT_SECRET.decode("utf-8"))
    ap.add_argument("--csv", default="requester_results.csv")
    args = ap.parse_args()

    random.seed(1)
    contexts = [c.strip() for c in args.contexts.split(",") if c.strip()]
    sleep_s = 1.0 / args.rate if args.rate > 0 else 0.0
    rows: List[Dict[str, object]] = []

    print(f"[requester] role={args.role} server={args.server}:{args.port} requests={args.requests} rate={args.rate}/s", flush=True)

    for i in range(args.requests):
        if args.role == "honest":
            requester_id = f"honest-{i % max(args.identities, 1)}"
            context = args.difficulty_context
        else:
            requester_id = f"sybil-{i % max(args.identities, 1)}"
            context = random.choice(contexts)

        row = one_request(args, requester_id, context)
        rows.append(row)
        write_row(args.csv, row)

        if (i + 1) % 10 == 0:
            acc = sum(int(r["accepted"]) for r in rows)
            totals = [float(r["total_exchange_ms"]) for r in rows if str(r["status"]).startswith(("accepted", "rejected"))]
            solves = [float(r["solve_ms"]) for r in rows if str(r["solve_ms"]) != "nan"]
            print(
                f"[requester] done={i+1}/{args.requests} accepted={acc} "
                f"median_total={percentile(totals, 0.50):.2f}ms p95_total={percentile(totals, 0.95):.2f}ms "
                f"median_solve={percentile(solves, 0.50):.2f}ms",
                flush=True,
            )

        if sleep_s > 0:
            time.sleep(sleep_s)

    totals = [float(r["total_exchange_ms"]) for r in rows if str(r["status"]).startswith(("accepted", "rejected"))]
    solves = [float(r["solve_ms"]) for r in rows if str(r["solve_ms"]) != "nan"]
    chall = [float(r["challenge_rtt_ms"]) for r in rows if str(r["challenge_rtt_ms"]) != "nan"]
    resrtt = [float(r["result_rtt_ms"]) for r in rows if str(r["result_rtt_ms"]) != "nan"]
    accepted = sum(int(r["accepted"]) for r in rows)

    print("\n=== SUMMARY ===")
    print(f"requests={len(rows)} accepted={accepted}")
    print(f"median_total_ms={percentile(totals, 0.50):.3f} p95_total_ms={percentile(totals, 0.95):.3f}")
    print(f"median_challenge_rtt_ms={percentile(chall, 0.50):.3f} p95_challenge_rtt_ms={percentile(chall, 0.95):.3f}")
    print(f"median_result_rtt_ms={percentile(resrtt, 0.50):.3f} p95_result_rtt_ms={percentile(resrtt, 0.95):.3f}")
    print(f"median_solve_ms={percentile(solves, 0.50):.3f} p95_solve_ms={percentile(solves, 0.95):.3f}")
    print(f"csv={args.csv}")


if __name__ == "__main__":
    main()
