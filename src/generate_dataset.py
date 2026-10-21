#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate synthetic network-flow data (CICIDS2017-like feature structure).

Run: python3 generate_dataset.py --out ../data/network_flows.csv --n 20000
"""

import argparse
import numpy as np
import pandas as pd

RNG_SEED = 42

LABELS = ["BENIGN", "DoS", "DDoS", "PortScan", "BruteForce", "WebAttack", "Botnet"]
LABEL_WEIGHTS = [0.74, 0.08, 0.07, 0.06, 0.03, 0.01, 0.01]  # intentional class imbalance


def make_flow_features(n, label, rng):
    """Generate flow features for one label, each with its own statistical center."""
    if label == "BENIGN":
        duration = rng.gamma(2.0, 0.8, n)
        fwd_pkts = rng.poisson(12, n)
        bwd_pkts = rng.poisson(10, n)
        fwd_bytes = rng.normal(600, 150, n).clip(40, None)
        bwd_bytes = rng.normal(550, 140, n).clip(40, None)
        syn_ratio = rng.beta(1, 8, n)
        pkt_rate = rng.normal(8, 3, n).clip(0.1, None)
    elif label == "DoS":
        duration = rng.gamma(1.2, 0.3, n)
        fwd_pkts = rng.poisson(220, n)
        bwd_pkts = rng.poisson(5, n)
        fwd_bytes = rng.normal(120, 40, n).clip(20, None)
        bwd_bytes = rng.normal(60, 20, n).clip(10, None)
        syn_ratio = rng.beta(6, 2, n)
        pkt_rate = rng.normal(180, 40, n).clip(1, None)
    elif label == "DDoS":
        duration = rng.gamma(1.0, 0.2, n)
        fwd_pkts = rng.poisson(400, n)
        bwd_pkts = rng.poisson(3, n)
        fwd_bytes = rng.normal(90, 30, n).clip(20, None)
        bwd_bytes = rng.normal(40, 15, n).clip(10, None)
        syn_ratio = rng.beta(8, 1.5, n)
        pkt_rate = rng.normal(320, 60, n).clip(1, None)
    elif label == "PortScan":
        duration = rng.gamma(0.8, 0.15, n)
        fwd_pkts = rng.poisson(3, n) + 1
        bwd_pkts = rng.poisson(1, n)
        fwd_bytes = rng.normal(48, 10, n).clip(20, None)
        bwd_bytes = rng.normal(44, 10, n).clip(0, None)
        syn_ratio = rng.beta(9, 1, n)
        pkt_rate = rng.normal(60, 20, n).clip(1, None)
    elif label == "BruteForce":
        duration = rng.gamma(3.0, 1.0, n)
        fwd_pkts = rng.poisson(35, n)
        bwd_pkts = rng.poisson(33, n)
        fwd_bytes = rng.normal(180, 50, n).clip(30, None)
        bwd_bytes = rng.normal(170, 50, n).clip(30, None)
        syn_ratio = rng.beta(3, 4, n)
        pkt_rate = rng.normal(22, 6, n).clip(0.5, None)
    elif label == "WebAttack":
        duration = rng.gamma(2.2, 0.9, n)
        fwd_pkts = rng.poisson(18, n)
        bwd_pkts = rng.poisson(14, n)
        fwd_bytes = rng.normal(900, 300, n).clip(50, None)
        bwd_bytes = rng.normal(700, 250, n).clip(50, None)
        syn_ratio = rng.beta(2, 6, n)
        pkt_rate = rng.normal(10, 4, n).clip(0.2, None)
    else:  # Botnet
        duration = rng.gamma(4.0, 1.5, n)
        fwd_pkts = rng.poisson(6, n) + 1
        bwd_pkts = rng.poisson(5, n) + 1
        fwd_bytes = rng.normal(260, 90, n).clip(30, None)
        bwd_bytes = rng.normal(240, 90, n).clip(30, None)
        syn_ratio = rng.beta(2, 5, n)
        pkt_rate = rng.normal(3, 1.2, n).clip(0.05, None)

    total_pkts = fwd_pkts + bwd_pkts
    total_bytes = fwd_bytes * fwd_pkts + bwd_bytes * bwd_pkts
    df = pd.DataFrame({
        "flow_duration_s": duration,
        "total_fwd_packets": fwd_pkts,
        "total_bwd_packets": bwd_pkts,
        "fwd_pkt_len_mean": fwd_bytes,
        "bwd_pkt_len_mean": bwd_bytes,
        "total_packets": total_pkts,
        "total_bytes": total_bytes,
        "packets_per_sec": pkt_rate,
        "bytes_per_sec": total_bytes / duration.clip(min=1e-3),
        "syn_flag_ratio": syn_ratio,
        "rst_flag_ratio": rng.beta(1, 15, n),
        "fwd_bwd_pkt_ratio": (fwd_pkts + 1) / (bwd_pkts + 1),
        "label": label,
    })
    return df


def inject_noise(df, rng, missing_frac=0.004, inf_frac=0.002):
    """Inject some missing/inf values to exercise the cleaning step."""
    n = len(df)
    numeric_cols = df.columns.drop("label")
    n_missing = int(n * missing_frac)
    n_inf = int(n * inf_frac)
    for _ in range(n_missing):
        r = rng.integers(0, n)
        c = rng.choice(numeric_cols)
        df.loc[r, c] = np.nan
    for _ in range(n_inf):
        r = rng.integers(0, n)
        c = rng.choice(numeric_cols)
        df.loc[r, c] = np.inf if rng.random() < 0.5 else -np.inf
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="../data/network_flows.csv")
    ap.add_argument("--n", type=int, default=20000, help="Tong so luong (flow) can sinh")
    args = ap.parse_args()

    rng = np.random.default_rng(RNG_SEED)
    counts = (np.array(LABEL_WEIGHTS) * args.n).astype(int)
    counts[0] += args.n - counts.sum()  # keep total == args.n

    frames = []
    for label, n in zip(LABELS, counts):
        if n <= 0:
            continue
        frames.append(make_flow_features(n, label, rng))

    df = pd.concat(frames, ignore_index=True)
    df = df.sample(frac=1.0, random_state=RNG_SEED).reset_index(drop=True)
    df = inject_noise(df, rng)

    df.to_csv(args.out, index=False)
    print(f"[generate_dataset] Da sinh {len(df)} ban ghi -> {args.out}")
    print(df["label"].value_counts())


if __name__ == "__main__":
    main()
