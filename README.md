# IDBA Artifact Code

This archive contains two pieces of code for the IDBA paper:

1. `prototype/`: a minimal multi-host Python prototype for IDBA and a KeyChallenge-style baseline.
2. `simulation/`: compact simulation scripts that regenerate the main evaluation CSVs and figures.

The code is intended as an artifact for paper validation and reproducibility, not as production overlay software.

---

## Directory layout

```text
idba_artifact_code/
  prototype/
    idba_common.py
    verifier.py
    requester.py
    summarize_results.py
  simulation/
    sim_common.py
    closed_form.py
    stochastic_sim.py
    network_sim.py
    run_all.py
  figures/
    generated outputs go here
```

---

## Requirements

Prototype:

- Python 3.10+
- no third-party Python packages

Simulation:

- Python 3.10+
- `numpy`
- `matplotlib`

Install simulation dependencies:

```bash
python3 -m pip install numpy matplotlib
```

---

# Part 1: Multi-host mini-prototype

## Topology

Use three Linux PCs on the same LAN:

```text
PC2 honest requester  ─┐
                       ├── LAN switch/router ── PC1 verifier
PC3 attacker requester ─┘
```

| PC | Role | Example IP | Program |
|---|---|---:|---|
| PC1 | verifier | `192.168.1.10` | `verifier.py` |
| PC2 | honest requester | `192.168.1.11` | `requester.py --role honest` |
| PC3 | attacker requester | `192.168.1.12` | `requester.py --role attacker` |

The paper experiment used commodity Linux PCs on a 1 Gbps LAN.

## Optional network sanity check

On PC1:

```bash
iperf3 -s
```

On PC2 and PC3:

```bash
iperf3 -c 192.168.1.10
```

## Experiment A: IDBA

On PC1:

```bash
cd prototype
python3 verifier.py \
  --host 0.0.0.0 \
  --port 9000 \
  --policy idba \
  --difficulty 18 \
  --adapt simple \
  --csv verifier_idba_3host.csv
```

On PC2:

```bash
cd prototype
python3 requester.py \
  --server 192.168.1.10 \
  --port 9000 \
  --role honest \
  --requests 600 \
  --identities 5 \
  --rate 5 \
  --difficulty-context default \
  --csv honest_idba_3host.csv
```

On PC3:

```bash
cd prototype
python3 requester.py \
  --server 192.168.1.10 \
  --port 9000 \
  --role attacker \
  --requests 600 \
  --identities 100 \
  --rate 20 \
  --contexts default,committee,reward,hotspot \
  --csv attacker_idba_3host.csv
```

## Experiment B: KeyChallenge-style baseline

Stop the verifier on PC1, then run:

```bash
cd prototype
python3 verifier.py \
  --host 0.0.0.0 \
  --port 9000 \
  --policy keychallenge \
  --difficulty 18 \
  --adapt fixed \
  --csv verifier_keychallenge_3host.csv
```

Run the same requester workloads again:

On PC2:

```bash
python3 requester.py \
  --server 192.168.1.10 \
  --port 9000 \
  --role honest \
  --requests 600 \
  --identities 5 \
  --rate 5 \
  --difficulty-context default \
  --csv honest_keychallenge_3host.csv
```

On PC3:

```bash
python3 requester.py \
  --server 192.168.1.10 \
  --port 9000 \
  --role attacker \
  --requests 600 \
  --identities 100 \
  --rate 20 \
  --contexts default,committee,reward,hotspot \
  --csv attacker_keychallenge_3host.csv
```

## Summarize prototype results

Copy requester CSVs to one machine, then run:

```bash
cd prototype
python3 summarize_results.py \
  honest_idba_3host.csv \
  attacker_idba_3host.csv \
  honest_keychallenge_3host.csv \
  attacker_keychallenge_3host.csv
```

Expected paper-style table columns:

- policy/workload
- median challenge RTT
- median solve time
- median verifier check time
- difficulty range

---

# Part 2: Simulation scripts

Run all simulations:

```bash
cd simulation
python3 run_all.py
```

Outputs are written to:

```text
figures/
```

Generated figures include:

- `fig_budget_scaling.pdf`
- `fig_suspicious_share.pdf`
- `fig_stochastic_budget.pdf`
- `fig_freshness_probe.pdf`
- `fig_network_size.pdf`
- `fig_committee_capture.pdf`
- `fig_adaptive_ablation.pdf`

Generated CSVs include corresponding numeric data.

## Individual scripts

Closed-form analysis:

```bash
python3 closed_form.py --out ../figures
```

Stochastic admission-event simulator:

```bash
python3 stochastic_sim.py --out ../figures --trials 200
```

Network-style simulator:

```bash
python3 network_sim.py --out ../figures
```

---

## Notes for paper use

- The prototype validates the admission exchange across real hosts. It is not a production DHT implementation.
- The KeyChallenge-style baseline is a same-harness static key-bound puzzle, not a full reproduction of the original system.
- The simulation scripts are compact reproducibility code for the reported trends and figures.
- Absolute numbers depend on workload, hardware, topology, and coefficients; the main claim is the consistent ordering among policy families.


---

## Included raw results

Raw CSV files for the three-host mini-prototype are included under `results/prototype/`. They can be summarized with:

```bash
cd prototype
python3 summarize_results.py ../results/prototype/*.csv
```

The files correspond to honest and attacker workloads for both IDBA and the KeyChallenge-style baseline.
