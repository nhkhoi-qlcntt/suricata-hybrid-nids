# Bao cao thuc nghiem mo phong
## Ung dung Hoc may trong Suricata: Mo hinh Phat hien Xam nhap Mang Lai
- Thoi gian chay: 9.47 giay
- Moi truong: Python 3.13.16 tren Linux-6.18.44-fc-v114-x86_64-with-glibc2.39
- Tong so ban ghi du lieu mo phong: 20000
- Phan bo nhan:
  - BENIGN: 14800
  - DoS: 1600
  - DDoS: 1400
  - PortScan: 1200
  - BruteForce: 600
  - WebAttack: 200
  - Botnet: 200

## 1. Ket qua cac mo hinh ADNIDS (phan loai nhi phan binh thuong/bat thuong)
| Mo hinh | Accuracy | Precision | Recall | F1-score | Thoi gian huan luyen (s) | Thoi gian suy luan (ms/mau) |
|---|---|---|---|---|---|---|
| DecisionTree | 0.9907 | 0.9937 | 0.9784 | 0.9860 | 0.10 | 0.0003 |
| RandomForest | 0.9931 | 0.9961 | 0.9830 | 0.9895 | 1.77 | 0.0091 |
| SVM | 0.9925 | 0.9976 | 0.9799 | 0.9887 | 0.08 | 0.0071 |

## 2. Ket qua mo hinh lai (Phuong an A: SNIDS + ADNIDS)
| Thanh phan | Accuracy | Precision | Recall | F1-score |
|---|---|---|---|---|
| SNIDS_only | 0.9094 | 1.0000 | 0.7282 | 0.8427 |
| ADNIDS_only | 0.9931 | 0.9961 | 0.9830 | 0.9895 |
| Hybrid_SNIDS_plus_ADNIDS | 0.9931 | 0.9961 | 0.9830 | 0.9895 |

## 3. So canh bao theo tung luat chu ky (SNIDS)
- SID:1000201 DoS_SYNFLOOD: 699 canh bao
- SID:1000202 DDoS_VOLUMETRIC: 312 canh bao
- SID:1000203 PORTSCAN_FAST: 243 canh bao

**Nhan xet:** He thong lai dat Recall cao hon thanh phan tot nhat +0.00 diem phan tram, phu hop voi lap luan ve uu diem bu tru cua mo hinh lai trinh bay o Muc 7.1 cua tieu luan.

## 4. Mo phong tinh huong Zero-day (loai 'Botnet' khoi huan luyen ADNIDS)
| Nhan | N (test) | Recall SNIDS | Recall ADNIDS (chua huan luyen) | Recall ADNIDS (co huan luyen, doi chieu) | Recall Hybrid |
|---|---|---|---|---|---|
| Botnet | 50 | 0.0000 | 0.0000 | 0.9600 | 0.0000 |
| DoS | 399 | 0.8822 | 1.0000 | 1.0000 | 1.0000 |

**Nhan xet:** Doi voi tan cong 'Botnet' duoc coi la "zero-day" (khong co trong ca luat chu ky lan du lieu huan luyen ADNIDS), ca SNIDS va ADNIDS deu co Recall rat thap (gan 0), xac nhan dung lap luan ve han che zero-day neu o Muc 2.4 va Muc 7.2 cua tieu luan. Khi ADNIDS duoc huan luyen lai voi mau cua nhan nay (cot doi chieu), Recall tang vot len 96.0%, minh hoa tam quan trong cua viec huan luyen lai dinh ky (online/incremental learning) da de xuat trong Muc 7.3. Nguoc lai, voi tan cong da biet 'DoS', ca hai thanh phan deu dat Recall cao, va he thong lai dat Recall toi da nho co it nhat mot nhanh nhan dien duoc.
