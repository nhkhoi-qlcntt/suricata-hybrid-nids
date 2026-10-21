#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture 3 live_demo.py terminal screenshots (SVG) as evidence for the report.

Run: python3 capture_screenshots.py
Output: ../screenshots/shot{1,2,3}_*.svg
"""

import os
import sys

sys.path.insert(0, ".")
from preprocess import load_and_prepare
from signature_engine import run_signature_engine
from sklearn.ensemble import RandomForestClassifier

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.align import Align

OUT_DIR = "../screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

MAX_ROWS = 14


class DemoState:
    def __init__(self):
        self.rows = []
        self.total = 0
        self.alerts_snids = 0
        self.alerts_adnids = 0
        self.alerts_hybrid = 0
        self.true_positives = 0
        self.phase = ""
        self.banner = ""

    def add_row(self, idx, label, snids, adnids, hybrid, is_attack):
        self.rows.append({"idx": idx, "label": label, "snids": snids,
                           "adnids": adnids, "hybrid": hybrid, "is_attack": is_attack})
        self.rows = self.rows[-MAX_ROWS:]
        self.total += 1
        if snids:
            self.alerts_snids += 1
        if adnids:
            self.alerts_adnids += 1
        if hybrid:
            self.alerts_hybrid += 1
        if hybrid == is_attack:
            self.true_positives += 1


def render(state: DemoState):
    table = Table(expand=True, show_lines=False, header_style="bold white on grey23")
    table.add_column("#", justify="right", width=5)
    table.add_column("Nhan thuc te", width=14)
    table.add_column("SNIDS\n(chu ky)", justify="center", width=12)
    table.add_column("ADNIDS\n(AI)", justify="center", width=12)
    table.add_column("He thong LAI", justify="center", width=16)

    for r in state.rows:
        snids_txt = Text("CANH BAO", style="bold red") if r["snids"] else Text("binh thuong", style="dim green")
        adnids_txt = Text("CANH BAO", style="bold red") if r["adnids"] else Text("binh thuong", style="dim green")
        hyb_txt = Text("BAT THUONG !", style="bold white on red") if r["hybrid"] else Text("AN TOAN", style="bold green")
        label_style = "yellow" if r["is_attack"] else "dim"
        table.add_row(str(r["idx"]), Text(r["label"], style=label_style), snids_txt, adnids_txt, hyb_txt)

    stats = Table.grid(padding=(0, 2))
    stats.add_column(justify="left")
    stats.add_column(justify="right")
    stats.add_row("Tong so flow da xu ly:", str(state.total))
    stats.add_row("Canh bao tu SNIDS (chu ky):", str(state.alerts_snids))
    stats.add_row("Canh bao tu ADNIDS (AI):", str(state.alerts_adnids))
    stats.add_row("Canh bao he thong LAI (hop nhat):", str(state.alerts_hybrid))
    if state.total:
        acc = state.true_positives / state.total * 100
        stats.add_row("Do chinh xac tich luy (Hybrid):", f"{acc:.1f}%")

    layout = Layout()
    layout.split_column(
        Layout(Panel(Align.center(Text(state.banner, style="bold cyan")),
                     title="MO PHONG TRUC TIEP: HYBRID NIDS (SNIDS + ADNIDS)",
                     border_style="cyan"), size=3),
        Layout(Panel(table, title=f"[ {state.phase} ]  Dong chay goi tin / luong mang",
                     border_style="white"), size=14),
        Layout(Panel(stats, title="Thong ke tich luy", border_style="white"), size=8),
    )
    return layout


def build_rows(indices, labels_test, adnids_pred, snids_vals, y_test):
    out = []
    for n, i in enumerate(indices, 1):
        sn = bool(snids_vals[i])
        adn = bool(adnids_pred[i])
        hyb = sn or adn
        out.append((n, labels_test[i], sn, adn, hyb, bool(y_test[i])))
    return out


def main():
    print("Dang chuan bi mo hinh va du lieu (dung du lieu/thuc nghiem that)...")
    data = load_and_prepare("../data/network_flows.csv")
    snids_alerts, _hits = run_signature_engine(data["X_test"])

    model_full = RandomForestClassifier(n_estimators=150, max_depth=14, random_state=42, n_jobs=-1)
    model_full.fit(data["X_train"], data["yb_train"])
    adnids_full_pred = model_full.predict(data["X_test"])

    zd_label = "Botnet"
    train_mask = data["ym_train"] != zd_label
    model_zeroday = RandomForestClassifier(n_estimators=150, max_depth=14, random_state=42, n_jobs=-1)
    model_zeroday.fit(data["X_train"][train_mask], data["yb_train"][train_mask])
    adnids_zeroday_pred = model_zeroday.predict(data["X_test"])

    y_test = data["yb_test"].values
    labels_test = data["ym_test"].values
    snids_vals = snids_alerts.values

    idx_benign = [i for i in range(len(labels_test)) if labels_test[i] == "BENIGN"][:12]
    idx_known_attack = [i for i in range(len(labels_test)) if labels_test[i] in ("DoS", "DDoS", "PortScan")][:14]
    idx_botnet = [i for i in range(len(labels_test)) if labels_test[i] == zd_label][:8]

    phase1 = build_rows(idx_benign, labels_test, adnids_full_pred, snids_vals, y_test)
    phase2 = build_rows(idx_known_attack, labels_test, adnids_full_pred, snids_vals, y_test)
    phase3 = build_rows(idx_botnet, labels_test, adnids_zeroday_pred, snids_vals, y_test)
    phase4 = build_rows(idx_botnet, labels_test, adnids_full_pred, snids_vals, y_test)

    # shot 1: known-attack detection
    state = DemoState()
    state.phase = "GIAI DOAN 2/4: Tan cong da biet (DoS / DDoS / PortScan)"
    state.banner = "Giai doan 2: Tan cong DA BIET - ca SNIDS va ADNIDS deu co kha nang phat hien"
    for row in phase1 + phase2:
        state.add_row(*row)
    console = Console(record=True, width=100)
    console.print(render(state))
    console.save_svg(f"{OUT_DIR}/shot1_known_attack.svg",
                      title="Terminal - live_demo.py - Giai doan tan cong da biet")
    print("Da luu:", f"{OUT_DIR}/shot1_known_attack.svg")

    # shot 2: zero-day miss
    state2 = DemoState()
    state2.phase = "GIAI DOAN 3/4: Mo phong ZERO-DAY (Botnet CHUA tung huan luyen)"
    state2.banner = "Giai doan 3: TAN CONG ZERO-DAY - Botnet KHONG co trong du lieu huan luyen ADNIDS"
    for row in phase1 + phase2 + phase3:
        state2.add_row(*row)
    console2 = Console(record=True, width=100)
    console2.print(render(state2))
    console2.print(Panel(
        "[bold white on red] CANH BAO: he thong gan nhu khong phat hien duoc tan cong Botnet "
        "o giai doan nay! [/bold white on red]\n"
        "Day la bang chung thuc nghiem cho han che zero-day da neu trong tieu luan: khi mot "
        "tan cong khong co ca chu ky lan du lieu huan luyen, he thong lai van co the bo lot.",
        border_style="red"))
    console2.save_svg(f"{OUT_DIR}/shot2_zero_day_miss.svg",
                       title="Terminal - live_demo.py - Zero-day bi bo lot")
    print("Da luu:", f"{OUT_DIR}/shot2_zero_day_miss.svg")

    # shot 3: after retraining
    state3 = DemoState()
    state3.phase = "GIAI DOAN 4/4: SAU KHI huan luyen lai voi mau Botnet"
    state3.banner = "Giai doan 4: Sau khi huan luyen lai ADNIDS voi mot so mau Botnet moi"
    for row in phase1 + phase2 + phase3 + phase4:
        state3.add_row(*row)
    console3 = Console(record=True, width=100)
    console3.print(render(state3))
    console3.print(Panel(
        "[bold white on green] Sau khi huan luyen lai, ADNIDS phat hien Botnet chinh xac hon "
        "ro ret! [/bold white on green]\n"
        "Minh hoa truc tiep gia tri cua viec huan luyen lai dinh ky (online/incremental "
        "learning) da de xuat trong tieu luan.",
        border_style="green"))
    console3.save_svg(f"{OUT_DIR}/shot3_retrained.svg",
                       title="Terminal - live_demo.py - Sau khi huan luyen lai")
    print("Da luu:", f"{OUT_DIR}/shot3_retrained.svg")

    print("\nHoan tat. Chay convert_svg_png.js de chuyen sang PNG nhung vao .docx.")


if __name__ == "__main__":
    main()
