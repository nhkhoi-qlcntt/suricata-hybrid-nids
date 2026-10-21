#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zero-day simulation: exclude one attack label entirely from ADNIDS training,
then compare recall on it vs. a known label.

Run: python3 zero_day_experiment.py --inp ../data/network_flows.csv
"""

import argparse
import json
import sys

sys.path.insert(0, ".")
import numpy as np
from preprocess import load_and_prepare
from signature_engine import run_signature_engine
from sklearn.ensemble import RandomForestClassifier


def run_zero_day(data, zd="Botnet", kn="DoS"):
    train_mask = data["ym_train"] != zd  # exclude zd label from ADNIDS training
    X_train_zd = data["X_train"][train_mask]
    yb_train_zd = data["yb_train"][train_mask]

    model_zeroday = RandomForestClassifier(n_estimators=150, max_depth=14,
                                            random_state=42, n_jobs=-1)
    model_zeroday.fit(X_train_zd, yb_train_zd)

    model_full = RandomForestClassifier(n_estimators=150, max_depth=14,
                                         random_state=42, n_jobs=-1)
    model_full.fit(data["X_train"], data["yb_train"])

    def recall_on_label(model, label):
        mask = data["ym_test"] == label
        X_sub = data["X_test"][mask]
        if len(X_sub) == 0:
            return None, 0
        y_pred = model.predict(X_sub)
        return float(np.mean(y_pred == 1)), int(len(X_sub))

    snids_alerts, _hits = run_signature_engine(data["X_test"])

    def snids_recall_on_label(label):
        mask = (data["ym_test"] == label).values
        sub_alerts = snids_alerts.values[mask]
        if len(sub_alerts) == 0:
            return None, 0
        return float(np.mean(sub_alerts == 1)), int(len(sub_alerts))

    results = {}
    for label in [zd, kn]:
        r_zeroday_model, n = recall_on_label(model_zeroday, label)
        r_full_model, _ = recall_on_label(model_full, label)
        r_snids, _ = snids_recall_on_label(label)
        hybrid_recall = None
        if r_zeroday_model is not None and r_snids is not None:
            mask = (data["ym_test"] == label).values
            X_sub = data["X_test"][mask]
            adn_pred = model_zeroday.predict(X_sub)
            sn_pred = snids_alerts.values[mask]
            hybrid_pred = ((adn_pred == 1) | (sn_pred == 1)).astype(int)
            hybrid_recall = float(np.mean(hybrid_pred == 1))

        results[label] = {
            "n_test_samples": n,
            "recall_SNIDS_only": r_snids,
            "recall_ADNIDS_not_trained_on_this_label": r_zeroday_model,
            "recall_ADNIDS_trained_on_this_label (doi chieu)": r_full_model,
            "recall_Hybrid_not_trained_on_this_label": hybrid_recall,
        }

    print(f"\n=== MO PHONG ZERO-DAY: '{zd}' bi loai khoi huan luyen ADNIDS, "
          f"so sanh voi tan cong da biet '{kn}' ===")
    for label, r in results.items():
        print(f"\n-- Nhan: {label} (n={r['n_test_samples']} mau kiem tra) --")
        print(f"   Recall SNIDS (chu ky)                         : {r['recall_SNIDS_only']}")
        print(f"   Recall ADNIDS (KHONG duoc huan luyen voi nhan) : {r['recall_ADNIDS_not_trained_on_this_label']}")
        print(f"   Recall ADNIDS (CO duoc huan luyen, doi chieu)  : {r['recall_ADNIDS_trained_on_this_label (doi chieu)']}")
        print(f"   Recall Hybrid (SNIDS + ADNIDS chua duoc huan luyen): {r['recall_Hybrid_not_trained_on_this_label']}")

    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", default="../data/network_flows.csv")
    ap.add_argument("--zero_day_label", default="Botnet")
    ap.add_argument("--known_label", default="DoS")
    ap.add_argument("--out", default="../results/zero_day_metrics.json")
    args = ap.parse_args()

    data = load_and_prepare(args.inp)
    results = run_zero_day(data, zd=args.zero_day_label, kn=args.known_label)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[zero_day_experiment] Da luu ket qua -> {args.out}")


if __name__ == "__main__":
    main()
