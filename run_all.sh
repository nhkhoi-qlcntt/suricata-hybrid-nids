#!/usr/bin/env bash
# run_all.sh: install deps -> run full experiment (report_generator.py) -> live demo (live_demo.py)
# Usage: ./run_all.sh [--no-ui] [--speed fast|normal|slow]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RUN_UI=1
DEMO_SPEED="normal"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-ui)
      RUN_UI=0
      shift
      ;;
    --speed)
      DEMO_SPEED="${2:-normal}"
      shift 2
      ;;
    -h|--help)
      echo "Dung: ./run_all.sh [--no-ui] [--speed fast|normal|slow]"
      exit 0
      ;;
    *)
      echo "Tuy chon khong hop le: $1" >&2
      exit 1
      ;;
  esac
done

PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "LOI: khong tim thay python3 trong he thong. Vui long cai dat Python >= 3.9." >&2
  exit 1
fi

# Keeps the window open after the script finishes (e.g. when run by double-click)
# so the user can read the output before it closes. Edit freely if needed.
pause_before_exit() {
  echo
  echo "------------------------------------------------------------"
  echo " Nhan phim bat ky de dong cua so nay..."
  echo "------------------------------------------------------------"
  read -n 1 -s -r -t 300 || true  # 5 min timeout as a safety net
}

echo "============================================================"
echo " BUOC 1/3: Kiem tra va cai dat thu vien Python can thiet"
echo "============================================================"

PIP_EXTRA_ARGS=()
if "$PYTHON_BIN" -m pip install --help 2>/dev/null | grep -q "break-system-packages"; then
  PIP_EXTRA_ARGS+=("--break-system-packages")
fi

"$PYTHON_BIN" -m pip install -q -r requirements.txt "${PIP_EXTRA_ARGS[@]}" || {
  echo "CANH BAO: pip install gap van de, thu lai khong co --break-system-packages..." >&2
  "$PYTHON_BIN" -m pip install -q -r requirements.txt
}

if [[ "$RUN_UI" -eq 1 ]]; then
  if ! "$PYTHON_BIN" -c "import rich" >/dev/null 2>&1; then
    echo "Dang cai dat thu vien 'rich' (de hien thi giao dien truc quan)..."
    "$PYTHON_BIN" -m pip install -q rich "${PIP_EXTRA_ARGS[@]}" || "$PYTHON_BIN" -m pip install -q rich
  fi
fi

echo
echo "============================================================"
echo " BUOC 2/3: Chay toan bo thuc nghiem (du lieu - huan luyen -"
echo "           SNIDS - he thong lai - mo phong zero-day - bieu do)"
echo "============================================================"
mkdir -p "$SCRIPT_DIR/data" "$SCRIPT_DIR/results"
cd "$SCRIPT_DIR/src"
"$PYTHON_BIN" report_generator.py

echo
echo "Da xong buoc thuc nghiem. Ket qua: results/ (bieu do PNG, JSON, Markdown)"
echo "va file BaoCao_ThucNghiem_MoPhong.docx (xem lai bang: node build_report.js)."

if [[ "$RUN_UI" -eq 0 ]]; then
  echo
  echo "Da bo qua demo truc quan (--no-ui). Hoan tat."
  pause_before_exit
  exit 0
fi

echo
echo "============================================================"
echo " BUOC 3/3: Mo giao dien truc quan (TRUC TIEP) mo phong qua"
echo "           trinh tan cong - phat hien - canh bao - phan loai"
echo "============================================================"
echo "(Nhan Ctrl+C bat cu luc nao de dung xem truoc; so lieu o Buoc 2"
echo " da duoc luu lai day du du khong xem het phan nay.)"
echo
sleep 1

"$PYTHON_BIN" live_demo.py --speed "$DEMO_SPEED"

echo
echo "============================================================"
echo " HOAN TAT TOAN BO QUY TRINH MO PHONG."
echo " Xem lai so lieu/bieu do trong thu muc results/ hoac file"
echo " BaoCao_ThucNghiem_MoPhong.docx de biet chi tiet day du."
echo "============================================================"

pause_before_exit
exit 0
