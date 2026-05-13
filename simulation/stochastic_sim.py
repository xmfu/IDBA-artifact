#!/usr/bin/env python3
"""
Stochastic admission-event simulator.

This is a compact reproducible simulator for the policy-family comparisons,
freshness-window sensitivity, and verifier-probing sensitivity.
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

from sim_common import ensure_dir, write_csv, ci95


def interaction_cost(policy, is_suspicious, freshness_window=2, probe_discount=0.0):
    if policy == "B0":
        return 0.25
    if policy == "B1":
        return 1.20
    if policy == "B2":
        base = 1.20 * (4.0 if is_suspicious else 1.0)
        return max(0.25, (base / 2.0) * (2.0 / freshness_window) * (1.0 - probe_discount))
    if policy == "IDBA":
        base = 1.20 * (4.0 if is_suspicious else 1.0)
        return max(1.20, base * (1.0 - 0.30 * probe_discount))
    raise ValueError(policy)


def run_epoch(policy, budget, A=300, q=2, K=40, C=4, W=2, pA=0.65, n_probe=1, seed=0):
    rng = random.Random(seed)
    spent = defaultdict(float)
    success = defaultdict(int)

    probe_discount = min(0.25, 0.04 * max(0, n_probe - 1))

    # Greedy randomized interaction attempts until budget exhausted.
    remaining = budget
    attempts = 0
    while remaining > 0 and attempts < A * q * 20:
        ident = rng.randrange(A)
        is_suspicious = rng.random() < pA
        cost = interaction_cost(policy, is_suspicious, freshness_window=W, probe_discount=probe_discount)
        if remaining < cost:
            break
        remaining -= cost
        spent[ident] += cost
        success[ident] += 1
        attempts += 1

    useful = sum(1 for i in range(A) if success[i] >= q)
    return useful


def sweep_budget(out, trials=200):
    budgets = [30, 70, 110, 150, 180, 220, 260]
    policies = ["B0", "B1", "B2", "IDBA"]
    rows = []

    plt.figure(figsize=(5.0, 3.1))
    for pol in policies:
        means = []
        lows = []
        highs = []
        for B in budgets:
            vals = [run_epoch(pol, B, seed=1000*t + int(B)) for t in range(trials)]
            m, ci = ci95(vals)
            means.append(m); lows.append(ci); highs.append(ci)
            rows.append({"policy": pol, "B": B, "mean": m, "ci95": ci})
        plt.errorbar(budgets, means, yerr=highs, marker="o", capsize=2, label=pol)
    plt.xlabel("Attacker budget B (normalized units)")
    plt.ylabel("Useful attacker identities")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out / "fig_stochastic_budget.pdf")
    write_csv(out / "stochastic_budget.csv", rows)


def sweep_freshness_probe(out, trials=200):
    rows = []

    # Freshness W
    Wvals = [1, 2, 4]
    plt.figure(figsize=(5.2, 3.0))
    for pol in ["B2", "IDBA"]:
        means = []
        for W in Wvals:
            vals = [run_epoch(pol, 180, W=W, seed=2000*t+W) for t in range(trials)]
            m, ci = ci95(vals)
            rows.append({"experiment": "freshness", "policy": pol, "x": W, "mean": m, "ci95": ci})
            means.append(m)
        plt.plot(Wvals, means, marker="o", label=f"{pol} freshness")

    # Probing n_probe
    Pvals = [1, 3, 5, 10, 20]
    for pol in ["B2", "IDBA"]:
        means = []
        for p in Pvals:
            vals = [run_epoch(pol, 180, n_probe=p, seed=3000*t+p) for t in range(trials)]
            m, ci = ci95(vals)
            rows.append({"experiment": "probe", "policy": pol, "x": p, "mean": m, "ci95": ci})
            means.append(m)
        plt.plot(Pvals, means, marker="s", linestyle="--", label=f"{pol} probing")

    plt.xlabel("Freshness windows W / probe count n_probe")
    plt.ylabel("Useful attacker identities")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(out / "fig_freshness_probe.pdf")
    write_csv(out / "stochastic_freshness_probe.csv", rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../figures")
    ap.add_argument("--trials", type=int, default=200)
    args = ap.parse_args()
    out = ensure_dir(args.out)

    sweep_budget(out, args.trials)
    sweep_freshness_probe(out, args.trials)


if __name__ == "__main__":
    main()
