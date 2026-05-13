#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from idba_common import percentile


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fvals(rows, key):
    vals = []
    for r in rows:
        try:
            v = float(r[key])
            if v == v:
                vals.append(v)
        except Exception:
            pass
    return vals


def summarize(path):
    rows = load_rows(path)
    return {
        "file": str(path),
        "policy": rows[0].get("policy", "unknown") if rows else "unknown",
        "requests": len(rows),
        "accepted": sum(int(r.get("accepted", 0)) for r in rows),
        "median_total_ms": percentile(fvals(rows, "total_exchange_ms"), 0.50),
        "p95_total_ms": percentile(fvals(rows, "total_exchange_ms"), 0.95),
        "median_challenge_rtt_ms": percentile(fvals(rows, "challenge_rtt_ms"), 0.50),
        "p95_challenge_rtt_ms": percentile(fvals(rows, "challenge_rtt_ms"), 0.95),
        "median_result_rtt_ms": percentile(fvals(rows, "result_rtt_ms"), 0.50),
        "p95_result_rtt_ms": percentile(fvals(rows, "result_rtt_ms"), 0.95),
        "median_solve_ms": percentile(fvals(rows, "solve_ms"), 0.50),
        "p95_solve_ms": percentile(fvals(rows, "solve_ms"), 0.95),
        "median_verify_ms": percentile(fvals(rows, "verify_ms"), 0.50),
        "p95_verify_ms": percentile(fvals(rows, "verify_ms"), 0.95),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_files", nargs="+")
    args = ap.parse_args()

    summaries = [summarize(Path(p)) for p in args.csv_files]

    print("| File | Policy | Requests | Accepted | Median total ms | p95 total ms | Median solve ms | p95 solve ms | Median verify ms |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for s in summaries:
        print(
            f"| {s['file']} | {s['policy']} | {s['requests']} | {s['accepted']} | "
            f"{s['median_total_ms']:.2f} | {s['p95_total_ms']:.2f} | "
            f"{s['median_solve_ms']:.2f} | {s['p95_solve_ms']:.2f} | {s['median_verify_ms']:.4f} |"
        )


if __name__ == "__main__":
    main()
