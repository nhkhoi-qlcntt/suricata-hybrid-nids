# Bộ code mô phỏng thực nghiệm — Tiểu luận "Ứng dụng Học máy trong Suricata"

Bộ code này mô phỏng (simulate) toàn bộ kiến trúc Hybrid NIDS đã trình bày trong
tiểu luận **"Ứng dụng Học máy trong Suricata: Xây dựng Mô hình Phát hiện Xâm nhập
Mạng Lai (Hybrid NIDS)"**, cho phép chạy thực nghiệm thật bằng Python và tái lập
toàn bộ số liệu, biểu đồ trong file `BaoCao_ThucNghiem_MoPhong.docx`.

> **Lưu ý quan trọng:** vì bộ dữ liệu CICIDS2017 gốc rất lớn (hàng chục GB) và
> cần tải riêng từ Canadian Institute for Cybersecurity, bộ code này **tự sinh
> một bộ dữ liệu mô phỏng (synthetic)** có cùng cấu trúc đặc trưng và cùng kiểu
> mất cân bằng lớp như CICIDS2017 (xem `src/generate_dataset.py`). Đây là cách
> làm phổ biến cho mục đích minh họa/demo khi không thể tải bộ dữ liệu gốc —
> toàn bộ pipeline tiền xử lý — huấn luyện — đánh giá vẫn chạy trung thực và có
> thể thay bằng dữ liệu CICIDS2017 thật nếu có sẵn (xem mục "Dùng dữ liệu
> CICIDS2017 thật" bên dưới).

## 1. Cấu trúc thư mục

```
simulation/
├── README.md                      <- file này
├── requirements.txt                <- danh sách thư viện Python cần cài
├── run_all.sh                      <- *** CHẠY CÁI NÀY *** — tự động từ đầu đến cuối
├── build_report.js                 <- script dựng báo cáo .docx (cần Node.js + docx)
├── BaoCao_ThucNghiem_MoPhong.docx  <- báo cáo kết quả (đã tạo sẵn)
├── src/
│   ├── generate_dataset.py         <- sinh dữ liệu luồng mạng mô phỏng
│   ├── preprocess.py               <- làm sạch, cân bằng lớp, chia train/test
│   ├── signature_engine.py         <- mô phỏng SNIDS (luật kiểu Suricata)
│   ├── train_classifier.py         <- huấn luyện & đánh giá Decision Tree/RF/SVM
│   ├── hybrid_pipeline.py          <- kết hợp SNIDS + ADNIDS (Phương án A)
│   ├── zero_day_experiment.py      <- mô phỏng tình huống tấn công zero-day
│   ├── report_generator.py         <- điều phối toàn bộ thực nghiệm + xuất biểu đồ/số liệu
│   ├── live_demo.py                <- GIAO DIỆN TRỰC QUAN (terminal UI) xem trực tiếp
│   ├── capture_screenshots.py      <- chụp lại 3 ảnh giao diện (dùng để chèn vào tiểu luận)
│   └── svg_to_png.py               <- chuyển ảnh SVG chụp được sang PNG (cần Playwright)
├── data/                           <- dữ liệu mô phỏng được sinh ra (tạo khi chạy)
├── screenshots/                    <- 3 ảnh chụp giao diện đã chèn vào file tiểu luận .docx
└── results/                        <- biểu đồ PNG + số liệu JSON/Markdown (tạo khi chạy)
```

### Ảnh chụp giao diện đã chèn vào tiểu luận (Mục 6.3)

Thư mục `screenshots/` chứa 3 ảnh chụp thật của giao diện `live_demo.py` khi
chạy trên dữ liệu thực nghiệm, đã được chèn vào file `tieuluan_suricata_ml.docx`
(Mục 6.3) làm bằng chứng đã thực sự chạy thực nghiệm trên máy, không chỉ là
số liệu lý thuyết. Nếu muốn tự chụp lại ảnh khác (ví dụ sau khi chỉnh sửa
`live_demo.py`), chạy:

```bash
cd src
python3 capture_screenshots.py   # xuất ảnh .svg vào ../screenshots/
python3 svg_to_png.py            # chuyển .svg -> .png (cần: pip install playwright
                                  #   && playwright install chromium)
```

Nếu không muốn cài Playwright, cách đơn giản nhất là tự chụp màn hình
(screenshot) khi chạy `python3 live_demo.py` trực tiếp trên terminal của bạn.

## 0. Chạy nhanh nhất — MỘT LỆNH DUY NHẤT (khuyến nghị)

Không cần làm theo từng bước ở dưới — chỉ cần chạy file `run_all.sh`. Script
này tự động: cài thư viện còn thiếu → chạy toàn bộ thực nghiệm (sinh dữ liệu,
huấn luyện, SNIDS, hệ thống lai, mô phỏng zero-day, xuất biểu đồ) → sau đó mở
**giao diện trực quan** cho xem trực tiếp quá trình tấn công — phát hiện —
cảnh báo — phân loại diễn ra trên màn hình.

```bash
cd simulation
chmod +x run_all.sh     # chỉ cần làm 1 lần nếu file chưa có quyền thực thi
./run_all.sh
```

Các tuỳ chọn:

```bash
./run_all.sh --no-ui          # chỉ chạy thực nghiệm, KHÔNG mở giao diện trực quan
./run_all.sh --speed fast     # giao diện trực quan chạy nhanh hơn (fast / normal / slow)
./run_all.sh --speed slow     # chạy chậm, phù hợp khi thuyết trình/báo cáo
```

Sau khi chạy xong, cửa sổ **KHÔNG tự đóng ngay** — script sẽ dừng lại và hiện
dòng "Nhấn phím bất kỳ để đóng cửa sổ này...", để có đủ thời gian xem lại kết
quả (đặc biệt hữu ích nếu bạn mở file `run_all.sh` bằng cách nhấp đúp thay vì
gõ lệnh, vì khi đó cửa sổ terminal thường tự đóng ngay khi script kết thúc).
Chỉ cần nhấn một phím bất kỳ (hoặc đợi tối đa 5 phút) là cửa sổ sẽ tự đóng.
Muốn đổi cách dừng này (ví dụ đổi thời gian chờ, hoặc thêm thông báo riêng),
sửa hàm `pause_before_exit()` ở đầu file `run_all.sh` — đó là chỗ đã được
đánh dấu sẵn (`*** ĐÂY LÀ CHỖ ĐỂ ĐIỀN THÊM NỘI DUNG TUỲ CHỈNH ***`) để điền
thêm nếu muốn.

Script tự dò hệ điều hành và tự thêm `--break-system-packages` cho `pip`
khi cần (một số bản Linux mới yêu cầu cờ này), nên hầu như không cần chỉnh
sửa gì thêm.

## 2. Cài đặt môi trường

Yêu cầu Python ≥ 3.9. Cài các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

(Nếu dùng môi trường có nhiều phiên bản Python, hãy đảm bảo đang dùng đúng
`python3`/`pip3`. Có thể cần thêm `--break-system-packages` trên một số hệ
Linux mới, hoặc tạo virtualenv trước: `python3 -m venv venv && source
venv/bin/activate`.)

## 3. Chạy toàn bộ thực nghiệm (1 lệnh duy nhất)

```bash
cd src
python3 report_generator.py
```

Script này tự động thực hiện theo đúng thứ tự:

1. Sinh dữ liệu mô phỏng 20.000 bản ghi (`data/network_flows.csv`) — bỏ qua nếu
   file đã tồn tại.
2. Tiền xử lý: loại giá trị thiếu/vô hạn, loại đặc trưng hằng số, cân bằng lớp,
   chia tập huấn luyện/kiểm tra.
3. Huấn luyện và đánh giá 3 mô hình ADNIDS: Decision Tree, Random Forest, SVM.
4. Chạy bộ luật SNIDS (signature engine mô phỏng Suricata).
5. Chạy pipeline lai (Hybrid = SNIDS OR ADNIDS), so sánh với từng thành phần
   riêng lẻ.
6. Mô phỏng tình huống zero-day (loại hẳn một nhóm tấn công khỏi huấn luyện).
7. Vẽ 5 biểu đồ trắng-đen và xuất báo cáo tổng hợp.

Thời gian chạy thực tế trên máy chủ thử nghiệm: **khoảng 7–10 giây**.

### Kết quả sau khi chạy

```
results/
├── 01_class_distribution.png        <- phân bố các nhóm nhãn
├── 02_model_comparison.png          <- so sánh Decision Tree / Random Forest / SVM
├── 03_confusion_matrix_hybrid.png   <- ma trận nhầm lẫn của hệ thống lai
├── 04_hybrid_recall_comparison.png  <- so sánh Recall SNIDS/ADNIDS/Hybrid
├── 05_zero_day_simulation.png       <- kết quả mô phỏng zero-day
├── experiment_summary.json          <- TOÀN BỘ số liệu thô (để hậu kiểm)
└── experiment_report.md             <- báo cáo dạng Markdown, đọc được ngay
```

## 3b. Giao diện trực quan (live UI) — xem trực tiếp quá trình phát hiện

File `src/live_demo.py` mở một giao diện dòng lệnh (terminal UI, dùng thư
viện `rich`) phát lại các luồng mạng thật từ tập kiểm tra, lần lượt đi qua
từng thành phần, hiển thị TRỰC TIẾP trên màn hình:

- **SNIDS (mô phỏng Suricata)**: có khớp luật chữ ký hay không
- **ADNIDS (AI)**: mô hình Random Forest phân loại là tấn công hay bình thường
- **Hệ thống lai**: hợp nhất hai cảnh báo, hiện **BẤT THƯỜNG** màu đỏ khi phát hiện
- Một bảng thống kê cộng dồn (tổng số luồng, số cảnh báo mỗi tầng, độ chính xác)

Giao diện chạy theo 4 giai đoạn, đúng với mạch lập luận của tiểu luận:

1. **Lưu lượng bình thường** — không có cảnh báo nào, hệ thống im lặng.
2. **Tấn công đã biết** (DoS/DDoS/PortScan) — cả SNIDS và ADNIDS đều bắt được.
3. **Mô phỏng Zero-day** (Botnet — nhãn bị loại hoàn toàn khỏi huấn luyện
   ADNIDS) — minh hoạ trực quan lúc hệ thống **bỏ lọt** tấn công hoàn toàn mới
   (đúng Mục 2.4 / 7.2 của tiểu luận), kèm cảnh báo đỏ giải thích ý nghĩa.
4. **Sau khi huấn luyện lại** với một số mẫu Botnet — ADNIDS bắt đầu phát
   hiện được, minh hoạ giá trị của việc huấn luyện lại định kỳ (Mục 7.3).

Chạy riêng (đã có `run_all.sh` gọi sẵn, không bắt buộc chạy tay):

```bash
cd src
python3 live_demo.py                # tốc độ bình thường
python3 live_demo.py --speed fast   # chạy nhanh, phù hợp demo ngắn
python3 live_demo.py --speed slow   # chạy chậm, phù hợp khi thuyết trình
```

Nếu môi trường chưa có thư viện `rich`, script tự động chuyển sang in ra
dạng văn bản đơn giản (không màu) — vẫn hiển thị đầy đủ nội dung, không bị lỗi.

## 4. Chạy từng bước riêng lẻ (tuỳ chọn, để kiểm tra/khám phá)

Mỗi script trong `src/` cũng có thể chạy độc lập để xem chi tiết từng bước:

```bash
cd src
python3 generate_dataset.py --out ../data/network_flows.csv --n 20000
python3 preprocess.py --inp ../data/network_flows.csv
python3 train_classifier.py --inp ../data/network_flows.csv
python3 signature_engine.py
python3 hybrid_pipeline.py --inp ../data/network_flows.csv
python3 zero_day_experiment.py --inp ../data/network_flows.csv \
        --zero_day_label Botnet --known_label DoS
python3 live_demo.py                # giao diện trực quan (xem Mục 3b)
```

## 5. Dựng lại báo cáo Word (.docx) từ số liệu mới

Sau khi chạy `report_generator.py` (tạo `results/experiment_summary.json`),
nếu muốn dựng lại file `BaoCao_ThucNghiem_MoPhong.docx` với số liệu mới nhất:

```bash
# cần Node.js (>=18) và thư viện docx: npm install docx
node build_report.js
```

File docx mới sẽ được ghi đè tại `simulation/BaoCao_ThucNghiem_MoPhong.docx`.

## 6. Dùng dữ liệu CICIDS2017 thật (tuỳ chọn, nâng cao)

Nếu có sẵn tệp CSV của bộ dữ liệu CICIDS2017 thật (tải từ
<https://www.unb.ca/cic/datasets/ids-2017.html>), có thể thay thế bước sinh dữ
liệu mô phỏng:

1. Gộp các tệp CSV CICIDS2017 thành một tệp duy nhất, đổi tên cột `Label`
   thành `label`, và đổi tên các cột đặc trưng cho khớp với tên dùng trong
   `src/preprocess.py` (hoặc chỉnh lại danh sách cột trong file đó cho khớp
   với bộ dữ liệu thật).
2. Lưu tệp đã gộp vào `data/network_flows.csv` (ghi đè tệp mô phỏng).
3. Chạy lại `python3 report_generator.py` như bình thường — toàn bộ pipeline
   tiền xử lý/huấn luyện/đánh giá sẽ tự động chạy trên dữ liệu thật.

## 7. Giải thích nhanh ý nghĩa từng thực nghiệm

| Thực nghiệm | Mục đích | Mục tương ứng trong tiểu luận |
|---|---|---|
| So sánh Decision Tree / Random Forest / SVM | Kiểm chứng hiệu năng các thuật toán ADNIDS | Mục 3.2, 6.2 |
| Hybrid pipeline (SNIDS + ADNIDS) | Kiểm chứng lợi ích bù trừ của mô hình lai | Mục 4.1, 7.1 |
| Mô phỏng Zero-day | Định lượng hạn chế khi gặp tấn công hoàn toàn mới | Mục 2.4, 7.2, 7.3 |


script tự động chuyển sang chế độ in văn bản đơn giản, vẫn chạy được đầy đủ,
không bị dừng. Nếu muốn giao diện đầy màu, nên chạy trong terminal hiện đại
(Windows Terminal, macOS Terminal/iTerm2, hầu hết terminal Linux).
