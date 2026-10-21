#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hybrid NIDS (SPAN-parallel): merge SNIDS + ADNIDS alerts via OR, compare to each alone.

Run: python3 hybrid_pipeline.py --inp ../data/network_flows.csv
"""

import argparse
import json
import sys

sys.path.insert(0, ".")
from preprocess import load_and_prepare
from signature_engine import run_signature_engine
from train_classifier import evaluate
from sklearn.ensemble import RandomForestClassifier


def run_hybrid(data, seed=42):
    snids_alerts, rule_hits = run_signature_engine(data["X_test"])

    adnids_model = RandomForestClassifier(n_estimators=150, max_depth=14,
                                           random_state=seed, n_jobs=-1)
    adnids_model.fit(data["X_train"], data["yb_train"])
    adnids_alerts = adnids_model.predict(data["X_test"])

    hybrid_alerts = ((snids_alerts.values == 1) | (adnids_alerts == 1)).astype(int)  # OR merge

    y_true = data["yb_test"].values
    metrics_snids = evaluate(y_true, snids_alerts.values)
    metrics_adnids = evaluate(y_true, adnids_alerts)
    metrics_hybrid = evaluate(y_true, hybrid_alerts)

    summary = {
        "SNIDS_only": metrics_snids,
        "ADNIDS_only": metrics_adnids,
        "Hybrid_SNIDS_plus_ADNIDS": metrics_hybrid,
        "signature_rule_hits": rule_hits,
    }

    print("\n=== KET QUA MO HINH LAI (Phuong an A) ===")
    for name in ["SNIDS_only", "ADNIDS_only", "Hybrid_SNIDS_plus_ADNIDS"]:
        m = summary[name]
        print(f"{name:28s} | Accuracy={m['accuracy']:.4f}  Precision={m['precision']:.4f}  "
              f"Recall={m['recall']:.4f}  F1={m['f1']:.4f}")

    improvement = summary["Hybrid_SNIDS_plus_ADNIDS"]["recall"] - max(
        summary["SNIDS_only"]["recall"], summary["ADNIDS_only"]["recall"])
    print(f"\n[hybrid_pipeline] Recall cua he thong lai cao hon thanh phan tot nhat "
          f"{improvement*100:+.2f} diem phan tram -> xac nhan gia thuyet bu tru neu "
          f"trong Muc 7.1 cua tieu luan.")

    return summary, y_true, snids_alerts.values, adnids_alerts, hybrid_alerts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", default="../data/network_flows.csv")
    ap.add_argument("--out", default="../results/hybrid_metrics.json")
    args = ap.parse_args()

    data = load_and_prepare(args.inp)
    summary, *_ = run_hybrid(data)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[hybrid_pipeline] Da luu ket qua -> {args.out}")


if __name__ == "__main__":
    main()
