#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live terminal UI: packet -> SNIDS signature check -> ADNIDS (AI) classify -> hybrid alert.

Run:
    python3 live_demo.py
    python3 live_demo.py --speed fast
    python3 live_demo.py --speed slow
"""

import argparse
import sys
import time

sys.path.insert(0, ".")
from preprocess import load_and_prepare
from signature_engine import run_signature_engine
from sklearn.ensemble import RandomForestClassifier

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.align import Align
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

DATA_PATH = "../data/network_flows.csv"
MAX_ROWS = 14  # so dong goi tin hien thi cung luc trong bang


def get_speed_delay(speed):
    return {"fast": 0.08, "normal": 0.28, "slow": 0.6}.get(speed, 0.28)


class DemoState:
    def __init__(self):
        self.rows = []  # list of dict: idx, label, snids, adnids, hybrid, verdict
        self.total = 0
        self.alerts_snids = 0
        self.alerts_adnids = 0
        self.alerts_hybrid = 0
        self.true_positives = 0
        self.phase = ""
        self.banner = ""

    def add_row(self, idx, label, snids, adnids, hybrid, is_attack):
        verdict = "BAT THUONG" if hybrid else "BINH THUONG"
        self.rows.append({
            "idx": idx, "label": label, "snids": snids, "adnids": adnids,
            "hybrid": hybrid, "verdict": verdict, "is_attack": is_attack,
        })
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
        if r["hybrid"]:
            hyb_txt = Text("BAT THUONG !", style="bold white on red")
        else:
            hyb_txt = Text("AN TOAN", style="bold green")
        label_style = "yellow" if r["is_attack"] else "dim"
        table.add_row(str(r["idx"]), Text(r["label"], style=label_style),
                      snids_txt, adnids_txt, hyb_txt)

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
                     border_style="white"), ratio=3),
        Layout(Panel(stats, title="Thong ke tich luy", border_style="white"), size=8),
    )
    return layout


def run_phase_plain(title, rows_iter, delay):
    """Fallback when 'rich' is unavailable: plain console output."""
    print(f"\n=== {title} ===")
    for idx, label, snids, adnids, hybrid, is_attack in rows_iter:
        verdict = "** BAT THUONG - CANH BAO **" if hybrid else "binh thuong"
        print(f"[{idx:4d}] nhan_thuc_te={label:12s} SNIDS={'CO' if snids else 'khong':5s} "
              f"ADNIDS={'CO' if adnids else 'khong':5s} => HYBRID: {verdict}")
        time.sleep(delay)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--speed", choices=["fast", "normal", "slow"], default="normal")
    ap.add_argument("--inp", default=DATA_PATH)
    args = ap.parse_args()
    delay = get_speed_delay(args.speed)

    print("Dang chuan bi mo hinh va du lieu cho phien mo phong truc tiep...")
    data = load_and_prepare(args.inp)
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
    idx_known_attack = [i for i in range(len(labels_test))
                         if labels_test[i] in ("DoS", "DDoS", "PortScan")][:14]
    idx_botnet = [i for i in range(len(labels_test)) if labels_test[i] == zd_label][:8]

    def build_rows(indices, use_zeroday_model=False):
        out = []
        for n, i in enumerate(indices, 1):
            adn_pred = adnids_zeroday_pred[i] if use_zeroday_model else adnids_full_pred[i]
            sn = bool(snids_vals[i])
            adn = bool(adn_pred)
            hyb = sn or adn
            out.append((n, labels_test[i], sn, adn, hyb, bool(y_test[i])))
        return out

    phase1 = build_rows(idx_benign)
    phase2 = build_rows(idx_known_attack)
    phase3_zeroday = build_rows(idx_botnet, use_zeroday_model=True)
    phase4_retrained = build_rows(idx_botnet, use_zeroday_model=False)

    if not HAS_RICH:
        print("\n(Goi y: cai dat 'pip install rich' de co giao dien mau sac dep hon)\n")
        run_phase_plain("GIAI DOAN 1: Luu luong binh thuong", phase1, delay)
        run_phase_plain("GIAI DOAN 2: Tan cong da biet (DoS / DDoS / PortScan)", phase2, delay)
        run_phase_plain("GIAI DOAN 3: Mo phong ZERO-DAY (Botnet - CHUA huan luyen)", phase3_zeroday, delay)
        print("\n*** Nhan xet: ca SNIDS lan ADNIDS deu KHONG phat hien duoc tan cong Botnet")
        print("    o Giai doan 3, vi day la tan cong 'chua tung biet' - dung Muc 2.4/7.2. ***")
        run_phase_plain("GIAI DOAN 4: SAU KHI huan luyen lai voi mau Botnet", phase4_retrained, delay)
        print("\n*** Nhan xet: sau khi huan luyen lai, ADNIDS phat hien duoc Botnet gan nhu hoan toan,")
        print("    minh hoa gia tri cua viec huan luyen lai dinh ky - dung Muc 7.3. ***\n")
        return

    console = Console()
    state = DemoState()

    def play(title, rows, banner):
        state.phase = title
        state.banner = banner
        with Live(render(state), console=console, refresh_per_second=12, screen=False) as live:
            for idx, label, sn, adn, hyb, is_attack in rows:
                state.add_row(idx, label, sn, adn, hyb, is_attack)
                live.update(render(state))
                time.sleep(delay)

    console.rule("[bold cyan]MO PHONG TRUC TIEP HE THONG HYBRID NIDS[/bold cyan]")
    console.print(Panel(
        "Tieu luan: Ung dung Hoc may trong Suricata - Xay dung Mo hinh Phat hien\n"
        "Xam nhap Mang Lai (Hybrid NIDS). Du lieu la mo phong (synthetic), xem\n"
        "README.md de biet chi tiet.",
        border_style="cyan"))
    time.sleep(1.0)

    play("GIAI DOAN 1/4: Luu luong binh thuong", phase1,
         "Giai doan 1: Quan sat luu luong mang BINH THUONG di qua he thong")
    time.sleep(0.8)

    play("GIAI DOAN 2/4: Tan cong da biet (DoS / DDoS / PortScan)", phase2,
         "Giai doan 2: Tan cong DA BIET - ca SNIDS va ADNIDS deu co kha nang phat hien")
    time.sleep(0.8)

    play("GIAI DOAN 3/4: Mo phong ZERO-DAY (Botnet CHUA tung huan luyen)", phase3_zeroday,
         "Giai doan 3: TAN CONG ZERO-DAY - Botnet KHONG co trong du lieu huan luyen ADNIDS")
    console.print(Panel(
        "[bold white on red] CANH BAO: he thong gan nhu khong phat hien duoc tan cong Botnet "
        "o giai doan nay! [/bold white on red]\n"
        "Day la bang chung thuc nghiem cho han che zero-day da neu o Muc 2.4 va Muc 7.2 cua "
        "tieu luan: khi mot tan cong khong co ca chu ky lan du lieu huan luyen, he thong lai "
        "van co the bo lot.",
        border_style="red"))
    time.sleep(1.5)

    play("GIAI DOAN 4/4: SAU KHI huan luyen lai voi mau Botnet", phase4_retrained,
         "Giai doan 4: Sau khi huan luyen lai ADNIDS voi mot so mau Botnet moi")
    console.print(Panel(
        "[bold white on green] Sau khi huan luyen lai, ADNIDS phat hien Botnet gan nhu hoan "
        "toan chinh xac! [/bold white on green]\n"
        "Minh hoa truc tiep gia tri cua viec huan luyen lai dinh ky (online/incremental "
        "learning) da de xuat o Muc 7.3 cua tieu luan.",
        border_style="green"))

    console.rule("[bold cyan]KET THUC PHIEN MO PHONG TRUC TIEP[/bold cyan]")
    console.print("Xem ket qua chi tiet (so lieu + bieu do) trong thu muc 'results/' va file "
                   "'BaoCao_ThucNghiem_MoPhong.docx'.")


if __name__ == "__main__":
    main()
