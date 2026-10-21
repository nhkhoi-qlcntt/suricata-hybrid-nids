#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preprocess network-flow data: clean, drop constant cols, balance classes, split.

Run: python3 preprocess.py --inp ../data/network_flows.csv
"""

import argparse
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def clean_missing_and_inf(df: pd.DataFrame) -> pd.DataFrame:
    df = df.replace([np.inf, -np.inf], np.nan)
    before = len(df)
    df = df.dropna(axis=0, how="any").reset_index(drop=True)
    after = len(df)
    print(f"[preprocess] Loai bo gia tri thieu/vo han: {before} -> {after} ban ghi "
          f"({before - after} ban ghi bi loai)")
    return df


def drop_constant_columns(df: pd.DataFrame, label_col="label") -> pd.DataFrame:
    numeric_cols = df.columns.drop(label_col)
    nunique = df[numeric_cols].nunique()
    const_cols = nunique[nunique <= 1].index.tolist()
    if const_cols:
        print(f"[preprocess] Loai {len(const_cols)} dac trung hang so: {const_cols}")
        df = df.drop(columns=const_cols)
    else:
        print("[preprocess] Khong co dac trung hang so can loai")
    return df


def balance_classes(df: pd.DataFrame, label_col="label", seed=42) -> pd.DataFrame:
    """Can bang lai ty le BENIGN/ATTACK bang undersampling lop BENIGN,
    tuong tu buoc can bang du lieu CICIDS2017 trong cac nghien cuu lien quan
    (Muc 5.1 tieu luan)."""
    counts = df[label_col].value_counts()
    attack_total = counts.drop("BENIGN", errors="ignore").sum()
    benign_target = min(counts.get("BENIGN", 0), attack_total * 2)

    benign_df = df[df[label_col] == "BENIGN"].sample(
        n=int(benign_target), random_state=seed)
    attack_df = df[df[label_col] != "BENIGN"]
    balanced = pd.concat([benign_df, attack_df], ignore_index=True)
    balanced = balanced.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    print(f"[preprocess] Can bang lop: BENIGN {counts.get('BENIGN', 0)} -> {len(benign_df)}, "
          f"tong du lieu sau can bang = {len(balanced)}")
    return balanced


def load_and_prepare(path: str, balance: bool = True, seed: int = 42):
    df = pd.read_csv(path)
    df = clean_missing_and_inf(df)
    df = drop_constant_columns(df)
    if balance:
        df = balance_classes(df, seed=seed)

    feature_cols = [c for c in df.columns if c != "label"]
    X = df[feature_cols]
    y_binary = (df["label"] != "BENIGN").astype(int)  # binary label for ADNIDS
    y_multiclass = df["label"]

    X_train, X_test, yb_train, yb_test, ym_train, ym_test = train_test_split(
        X, y_binary, y_multiclass, test_size=0.25, random_state=seed,
        stratify=y_multiclass,
    )
    print(f"[preprocess] Chia du lieu: {len(X_train)} huan luyen / {len(X_test)} kiem tra "
          f"({len(feature_cols)} dac trung)")
    return {
        "X_train": X_train, "X_test": X_test,
        "yb_train": yb_train, "yb_test": yb_test,
        "ym_train": ym_train, "ym_test": ym_test,
        "feature_cols": feature_cols,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inp", default="../data/network_flows.csv")
    args = ap.parse_args()
    data = load_and_prepare(args.inp)
    print("\n[preprocess] Phan bo nhan (tap huan luyen):")
    print(data["ym_train"].value_counts())


if __name__ == "__main__":
    main()
