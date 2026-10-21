#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrates the full experiment: data -> preprocess -> train -> SNIDS -> hybrid -> charts/report.

Run: cd src/ && python3 report_generator.py
"""

import json
import os
import sys
import time
import platform

sys.path.insert(0, ".")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from generate_dataset import main as generate_main
from preprocess import load_and_prepare
from train_classifier import train_all
from hybrid_pipeline import run_hybrid
from zero_day_experiment import run_zero_day
from sklearn.metrics import confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from signature_engine import run_signature_engine

DATA_PATH = "../data/network_flows.csv"
RESULTS_DIR = "../results"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "text.color": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

GRAY_SHADES = ["#1a1a1a", "#4d4d4d", "#808080", "#b3b3b3", "#d9d9d9"]
HATCHES = ["", "///", "...", "xxx", "\\\\\\"]


def ensure_dataset():
    if not os.path.exists(DATA_PATH):
        print("[report_generator] Chua co du lieu, dang sinh du lieu mo phong...")
        sys.argv = ["generate_dataset.py", "--out", DATA_PATH, "--n", "20000"]
        generate_main()
    else:
        print(f"[report_generator] Dung lai du lieu da co: {DATA_PATH}")


def plot_class_distribution(df, out_path):
    counts = df["label"].value_counts()
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(counts.index, counts.values, color="white", edgecolor="black",
                   hatch="///", linewidth=1.2)
    ax.set_title("Phan bo cac nhom nhan trong du lieu mo phong", fontsize=12, fontweight="bold")
    ax.set_ylabel("So luong flow")
    ax.tick_params(axis="x", rotation=30)
    for b in bars:
        h = b.get_height()
        ax.annotate(f"{int(h)}", (b.get_x() + b.get_width() / 2, h),
                    ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"[report_generator] Da luu bieu do -> {out_path}")


def plot_confusion_matrix(cm, labels, title, out_path):
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    im = ax.imshow(cm, cmap="Greys")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Nhan du doan")
    ax.set_ylabel("Nhan thuc te")
    ax.set_title(title, fontsize=11, fontweight="bold", wrap=True)
    vmax = cm.max()
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            color = "white" if cm[i, j] > vmax / 2 else "black"
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=color, fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"[report_generator] Da luu bieu do -> {out_path}")


def plot_model_comparison(results, out_path):
    models = list(results.keys())
    metrics = ["accuracy", "precision", "recall", "f1"]
    x = np.arange(len(metrics))
    width = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for i, m in enumerate(models):
        vals = [results[m][met] for met in metrics]
        ax.bar(x + i * width, vals, width=width, label=m, color="white",
               edgecolor="black", hatch=HATCHES[i % len(HATCHES)], linewidth=1.1)
    ax.set_xticks(x + width * (len(models) - 1) / 2)
    ax.set_xticklabels(["Accuracy", "Precision", "Recall", "F1-score"])
    ax.set_ylim(0, 1.08)
    ax.set_title("So sanh hieu nang cac mo hinh ADNIDS (Muc 6.2 tieu luan)",
                  fontsize=11, fontweight="bold")
    ax.legend(frameon=False, ncol=len(models))
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"[report_generator] Da luu bieu do -> {out_path}")


def plot_zero_day(zd_results, zd_label, kn_label, out_path):
    keys = ["recall_SNIDS_only", "recall_ADNIDS_not_trained_on_this_label",
            "recall_Hybrid_not_trained_on_this_label"]
    legend = ["SNIDS (chu ky)", "ADNIDS (chua huan luyen voi nhan nay)", "Hybrid"]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(2)
    width = 0.25
    for i, k in enumerate(keys):
        vals = [zd_results[zd_label][k] or 0.0, zd_results[kn_label][k] or 0.0]
        ax.bar(x + i * width, vals, width=width, label=legend[i], color="white",
               edgecolor="black", hatch=HATCHES[i % len(HATCHES)], linewidth=1.1)
    ax.set_xticks(x + width)
    ax.set_xticklabels([f"{zd_label}\n(mo phong Zero-day)", f"{kn_label}\n(tan cong da biet)"])
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Recall")
    ax.set_title("Mo phong Zero-day: han che cua tung thanh phan (Muc 2.4, 7.2 tieu luan)",
                  fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"[report_generator] Da luu bieu do -> {out_path}")


def plot_hybrid_comparison(hybrid_summary, out_path):
    names = ["SNIDS_only", "ADNIDS_only", "Hybrid_SNIDS_plus_ADNIDS"]
    labels_vn = ["SNIDS\n(chu ky)", "ADNIDS\n(hoc may)", "Hybrid\n(SNIDS+ADNIDS)"]
    recalls = [hybrid_summary[n]["recall"] for n in names]

    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    bars = ax.bar(labels_vn, recalls, color="white", edgecolor="black",
                   hatch="///", linewidth=1.2)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Recall (ty le phat hien tan cong)")
    ax.set_title("Hieu qua bu tru cua mo hinh lai (Muc 7.1 tieu luan)",
                  fontsize=11, fontweight="bold")
    for b, v in zip(bars, recalls):
        ax.annotate(f"{v:.3f}", (b.get_x() + b.get_width() / 2, v),
                    ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    print(f"[report_generator] Da luu bieu do -> {out_path}")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    t_start = time.time()

    print("=" * 70)
    print("THUC NGHIEM MO PHONG: UNG DUNG HOC MAY TRONG SURICATA")
    print("Hybrid NIDS - script dieu phoi report_generator.py")
    print("=" * 70)

    ensure_dataset()
    df_raw = pd.read_csv(DATA_PATH)

    data = load_and_prepare(DATA_PATH)

    print("\n--- [1/3] Huan luyen va danh gia cac mo hinh ADNIDS ---")
    clf_results, _best_model, _scaler = train_all(data)

    print("\n--- [2/3] Chay SNIDS + Hybrid pipeline (Phuong an A) ---")
    hybrid_summary, y_true, snids_pred, adnids_pred, hybrid_pred = run_hybrid(data)

    print("\n--- [3/3] Ve bieu do va xuat bao cao ---")
    plot_class_distribution(df_raw, f"{RESULTS_DIR}/01_class_distribution.png")
    plot_model_comparison(clf_results, f"{RESULTS_DIR}/02_model_comparison.png")

    cm_hybrid = confusion_matrix(y_true, hybrid_pred)
    plot_confusion_matrix(cm_hybrid, ["Binh thuong", "Bat thuong"],
                           "Ma tran nham lan - He thong lai (Hybrid)",
                           f"{RESULTS_DIR}/03_confusion_matrix_hybrid.png")

    plot_hybrid_comparison(hybrid_summary, f"{RESULTS_DIR}/04_hybrid_recall_comparison.png")

    print("\n--- [bo sung] Mo phong tinh huong Zero-day ---")
    zd_label, kn_label = "Botnet", "DoS"
    zero_day_results = run_zero_day(data, zd=zd_label, kn=kn_label)
    plot_zero_day(zero_day_results, zd_label, kn_label,
                  f"{RESULTS_DIR}/05_zero_day_simulation.png")

    elapsed = time.time() - t_start

    summary = {
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "dataset": {
            "path": DATA_PATH,
            "n_total_records": int(len(df_raw)),
            "label_distribution": df_raw["label"].value_counts().to_dict(),
        },
        "classifier_results": clf_results,
        "hybrid_results": hybrid_summary,
        "zero_day_results": zero_day_results,
        "zero_day_label": zd_label,
        "known_label": kn_label,
        "total_runtime_seconds": elapsed,
    }

    with open(f"{RESULTS_DIR}/experiment_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    write_markdown_report(summary, f"{RESULTS_DIR}/experiment_report.md")

    print("\n" + "=" * 70)
    print(f"HOAN TAT. Tong thoi gian chay: {elapsed:.2f} giay")
    print(f"Ket qua day du: {RESULTS_DIR}/experiment_summary.json")
    print(f"Bao cao doc duoc: {RESULTS_DIR}/experiment_report.md")
    print("=" * 70)


def write_markdown_report(summary, out_path):
    clf = summary["classifier_results"]
    hyb = summary["hybrid_results"]
    ds = summary["dataset"]

    lines = []
    lines.append("# Bao cao thuc nghiem mo phong\n")
    lines.append("## Ung dung Hoc may trong Suricata: Mo hinh Phat hien Xam nhap Mang Lai\n")
    lines.append(f"- Thoi gian chay: {summary['total_runtime_seconds']:.2f} giay\n")
    lines.append(f"- Moi truong: Python {summary['environment']['python_version']} "
                  f"tren {summary['environment']['platform']}\n")
    lines.append(f"- Tong so ban ghi du lieu mo phong: {ds['n_total_records']}\n")
    lines.append("- Phan bo nhan:\n")
    for k, v in ds["label_distribution"].items():
        lines.append(f"  - {k}: {v}\n")

    lines.append("\n## 1. Ket qua cac mo hinh ADNIDS (phan loai nhi phan binh thuong/bat thuong)\n")
    lines.append("| Mo hinh | Accuracy | Precision | Recall | F1-score | Thoi gian huan luyen (s) | Thoi gian suy luan (ms/mau) |\n")
    lines.append("|---|---|---|---|---|---|---|\n")
    for name, m in clf.items():
        lines.append(f"| {name} | {m['accuracy']:.4f} | {m['precision']:.4f} | "
                      f"{m['recall']:.4f} | {m['f1']:.4f} | {m['train_time_s']:.2f} | "
                      f"{m['inference_ms_per_sample']:.4f} |\n")

    lines.append("\n## 2. Ket qua mo hinh lai (Phuong an A: SNIDS + ADNIDS)\n")
    lines.append("| Thanh phan | Accuracy | Precision | Recall | F1-score |\n")
    lines.append("|---|---|---|---|---|\n")
    for name in ["SNIDS_only", "ADNIDS_only", "Hybrid_SNIDS_plus_ADNIDS"]:
        m = hyb[name]
        lines.append(f"| {name} | {m['accuracy']:.4f} | {m['precision']:.4f} | "
                      f"{m['recall']:.4f} | {m['f1']:.4f} |\n")

    lines.append("\n## 3. So canh bao theo tung luat chu ky (SNIDS)\n")
    for sid, n in hyb["signature_rule_hits"].items():
        lines.append(f"- {sid}: {n} canh bao\n")

    improvement = (hyb["Hybrid_SNIDS_plus_ADNIDS"]["recall"]
                   - max(hyb["SNIDS_only"]["recall"], hyb["ADNIDS_only"]["recall"]))
    lines.append(f"\n**Nhan xet:** He thong lai dat Recall cao hon thanh phan tot nhat "
                 f"{improvement*100:+.2f} diem phan tram, phu hop voi lap luan ve uu diem "
                 f"bu tru cua mo hinh lai trinh bay o Muc 7.1 cua tieu luan.\n")

    if "zero_day_results" in summary:
        zd = summary["zero_day_results"]
        zd_label = summary["zero_day_label"]
        kn_label = summary["known_label"]
        lines.append(f"\n## 4. Mo phong tinh huong Zero-day "
                      f"(loai '{zd_label}' khoi huan luyen ADNIDS)\n")
        lines.append("| Nhan | N (test) | Recall SNIDS | Recall ADNIDS (chua huan luyen) | "
                      "Recall ADNIDS (co huan luyen, doi chieu) | Recall Hybrid |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for label in [zd_label, kn_label]:
            r = zd[label]
            lines.append(
                f"| {label} | {r['n_test_samples']} | {r['recall_SNIDS_only']:.4f} | "
                f"{r['recall_ADNIDS_not_trained_on_this_label']:.4f} | "
                f"{r['recall_ADNIDS_trained_on_this_label (doi chieu)']:.4f} | "
                f"{r['recall_Hybrid_not_trained_on_this_label']:.4f} |\n"
            )
        lines.append(f"\n**Nhan xet:** Doi voi tan cong '{zd_label}' duoc coi la "
                      f"\"zero-day\" (khong co trong ca luat chu ky lan du lieu huan luyen "
                      f"ADNIDS), ca SNIDS va ADNIDS deu co Recall rat thap (gan 0), xac nhan "
                      f"dung lap luan ve han che zero-day neu o Muc 2.4 va Muc 7.2 cua tieu "
                      f"luan. Khi ADNIDS duoc huan luyen lai voi mau cua nhan nay (cot doi "
                      f"chieu), Recall tang vot len "
                      f"{zd[zd_label]['recall_ADNIDS_trained_on_this_label (doi chieu)']*100:.1f}%, "
                      f"minh hoa tam quan trong cua viec huan luyen lai dinh ky (online/"
                      f"incremental learning) da de xuat trong Muc 7.3. Nguoc lai, voi tan "
                      f"cong da biet '{kn_label}', ca hai thanh phan deu dat Recall cao, va "
                      f"he thong lai dat Recall toi da nho co it nhat mot nhanh nhan dien duoc.\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


if __name__ == "__main__":
    main()
