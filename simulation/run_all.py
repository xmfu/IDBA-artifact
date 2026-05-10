#!/usr/bin/env python3
"""
Run all simulation scripts and produce CSV/PDF outputs in ../figures.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "figures"
OUT.mkdir(exist_ok=True)

scripts = [
    "closed_form.py",
    "stochastic_sim.py",
    "network_sim.py",
]

for script in scripts:
    print(f"Running {script}...")
    subprocess.check_call([sys.executable, str(HERE / script), "--out", str(OUT)])

print(f"Done. Outputs written to {OUT}")
