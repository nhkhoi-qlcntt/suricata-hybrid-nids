#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SNIDS simulation: Suricata-style threshold rules.

Rules intentionally cover only DoS/DDoS/PortScan, not BruteForce/WebAttack/Botnet,
to demonstrate the zero-day detection gap.
"""

import pandas as pd


def rule_dos_synflood(row):
    return row["packets_per_sec"] > 100 and row["syn_flag_ratio"] > 0.55


def rule_ddos_volumetric(row):
    return row["packets_per_sec"] > 250 and row["total_fwd_packets"] > 200


def rule_portscan(row):
    return (row["total_packets"] < 8 and row["packets_per_sec"] > 30
            and row["syn_flag_ratio"] > 0.6)


SIGNATURES = [
    ("SID:1000201 DoS_SYNFLOOD", rule_dos_synflood, "DoS"),
    ("SID:1000202 DDoS_VOLUMETRIC", rule_ddos_volumetric, "DDoS"),
    ("SID:1000203 PORTSCAN_FAST", rule_portscan, "PortScan"),
]


def run_signature_engine(X: pd.DataFrame) -> pd.Series:
    """Tra ve Series nhi phan (1 = co canh bao chu ky, 0 = khong) cho tung dong."""
    alerts = pd.Series(0, index=X.index, dtype=int)
    hits_by_rule = {}
    for sid, rule_fn, _label in SIGNATURES:
        mask = X.apply(rule_fn, axis=1)
        hits_by_rule[sid] = int(mask.sum())
        alerts = alerts | mask.astype(int)
    return alerts, hits_by_rule


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from preprocess import load_and_prepare

    data = load_and_prepare("../data/network_flows.csv")
    alerts, hits = run_signature_engine(data["X_test"])
    print("[signature_engine] So canh bao theo tung luat (tap kiem tra):")
    for sid, n in hits.items():
        print(f"  {sid}: {n} canh bao")
    print(f"[signature_engine] Tong so flow co canh bao chu ky: {alerts.sum()} / {len(alerts)}")
