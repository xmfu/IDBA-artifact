#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from typing import Dict, List

import numpy as np


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_csv(path: str | Path, rows: List[Dict]):
    path = Path(path)
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def useful_identities_budget(B: float, q: float, effective_cost: float) -> float:
    return B / (q * effective_cost)


def effective_cost(policy: str, s: float = 0.4, lam: float = 4.0, base: float = 1.2, rho: float = 1.0) -> float:
    if policy == "B0":
        return 1.0 / 4.0
    if policy == "B1":
        return base
    if policy == "B2":
        return 0.5 * base * ((1 - s) + lam * s)
    if policy == "IDBA":
        return base * ((1 - s) + lam * s)
    raise ValueError(policy)


def ci95(values):
    arr = np.array(values, dtype=float)
    if len(arr) <= 1:
        return float(arr.mean()), 0.0
    return float(arr.mean()), float(1.96 * arr.std(ddof=1) / np.sqrt(len(arr)))
