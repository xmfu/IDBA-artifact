#!/usr/bin/env python3
"""
Closed-form budget sweeps for IDBA direct-baseline comparison.
Outputs CSV and PDF figures.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import matplotlib.pyplot as plt
import numpy as np

from sim_common import ensure_dir, write_csv, useful_identities_budget, effective_cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../figures")
    args = ap.parse_args()
    out = ensure_dir(args.out)

    q = 2
    budgets = np.array([0, 50, 100, 150, 200, 250], dtype=float)
    policies = ["B0", "B1", "B2", "IDBA"]

    rows = []
    plt.figure(figsize=(5.0, 3.1))
    for pol in policies:
        y = [useful_identities_budget(B, q, effective_cost(pol)) for B in budgets]
        plt.plot(budgets, y, marker="o", label=pol)
        for B, yy in zip(budgets, y):
            rows.append({"policy": pol, "B": B, "useful_identities": yy})
    plt.xlabel("Attacker budget B (normalized units)")
    plt.ylabel("Useful attacker identities")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out / "fig_budget_scaling.pdf")
    write_csv(out / "closed_form_budget.csv", rows)
    plt.close()

    svals = np.linspace(0, 1, 11)
    rows = []
    plt.figure(figsize=(5.0, 3.1))
    for pol in ["B1", "IDBA"]:
        y = [1 / (q * effective_cost(pol, s=s)) for s in svals]
        plt.plot(svals, y, marker="o", label=pol)
        for s, yy in zip(svals, y):
            rows.append({"policy": pol, "s": s, "useful_per_budget": yy})
    plt.xlabel("Suspicious fraction s")
    plt.ylabel("Useful identities per budget unit")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out / "fig_suspicious_share.pdf")
    write_csv(out / "closed_form_suspicious_share.csv", rows)


if __name__ == "__main__":
    main()
