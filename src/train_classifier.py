#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Train ADNIDS classifiers (Decision Tree, Random Forest, SVM) and evaluate.

Run: python3 train_classifier.py --inp ../data/network_flows.csv
"""

import argparse
import json
import sys
import time

sys.path.insert(0, ".")
from preprocess import load_and_prepare

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)


MODELS = {
    "DecisionTree": lambda: DecisionTreeClassifier(max_depth=10, random_state=42),
    "RandomForest": lambda: RandomForestClassifier(n_estimators=150, max_depth=14, random_state=42, n_jobs=-1),
    "SVM": lambda: SVC(kernel="rbf", C=4.0, gamma="scale", random_state=42),
}


def evaluate(y_true, y_pred):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def train_all(data, use_scaled_for_svm=True, sample_svm=6000, seed=42):
    """Huan luyen ca 3 mo hinh tren tap du lieu nhi phan (binh thuong/bat thuong).
    SVM duoc huan luyen tren mot tap con (sample_svm) de giu thoi gian chay
    hop ly trong moi truong demo, giong nhan xet ve chi phi tinh toan cua SVM/NN
    trong Muc 7.2 cua tieu luan."""
    results = {}
    timings = {}

    scaler = StandardScaler()
    Xtr_scaled = scaler.fit_transform(data["X_train"])
    Xte_scaled = scaler.transform(data["X_test"])

    for name, ctor in MODELS.items():
        model = ctor()
        t0 = time.perf_counter()

        if name == "SVM" and len(data["X_train"]) > sample_svm:
            Xtr = Xtr_scaled[:sample_svm]
            ytr = data["yb_train"].iloc[:sample_svm]
        elif name == "SVM":
            Xtr, ytr = Xtr_scaled, data["yb_train"]
        else:
            Xtr, ytr = data["X_train"], data["yb_train"]

        model.fit(Xtr, ytr)
        t_train = time.perf_counter() - t0

        Xte = Xte_scaled if name == "SVM" else data["X_test"]
        t1 = time.perf_counter()
        y_pred = model.predict(Xte)
        t_infer_total = time.perf_counter() - t1
        t_infer_per_sample_ms = (t_infer_total / len(Xte)) * 1000.0

        metrics = evaluate(data["yb_test"], y_pred)
        metrics["train_time_s"] = t_train
        metrics["inference_ms_per_sample"] = t_infer_per_sample_ms
        results[name] = metrics
        timings[name] = {"train_s": t_train, "infer_ms_per_sample": t_infer_per_sample_ms}

        print(f"[train_classifier] {name}: accuracy={metrics['accuracy']:.4f} "
              f"precision={metrics['precision']:.4f} recall={metrics['recall']:.4f} "
              f"f1={metrics['f1']:.4f} | train={t_train:.2f}s "
              f"infer={t_infer_per_sample_ms:.4f} ms/mau")

    best_model = MODELS["RandomForest"]()  # most stable model, used by the hybrid pipeline
    best_model.fit(data["X_train"], data["yb_train"])

    return results, best_model, scaler


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", default="../data/network_flows.csv")
    ap.add_argument("--out", default="../results/classifier_metrics.json")
    args = ap.parse_args()

    data = load_and_prepare(args.inp)
    results, _model, _scaler = train_all(data)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[train_classifier] Da luu ket qua -> {args.out}")


if __name__ == "__main__":
    main()
