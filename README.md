# GoldVN Data Pipeline

Project chuẩn bị dữ liệu cho mô hình phân tích lợi suất và biến động của ba tài sản:

- Bitcoin quy đổi sang VND.
- Vàng miếng SJC tại TPHCM.
- VN-Index.

Khoảng dữ liệu mặc định: từ `2023-08-01` đến hết `2026-08-01`.

## Nguồn dữ liệu

| Dữ liệu | Nguồn | Mã hoặc lựa chọn |
| --- | --- | --- |
| VN-Index | KBS thông qua `vnstock` | `VNINDEX` |
| Bitcoin | Yahoo Finance | `BTC-USD` |
| USD/VND | Yahoo Finance | `VND=X` |
| Vàng | PNJ | SJC, TPHCM |

## Cấu trúc project

```text
goldvn-data-pipeline/
├── README.md
├── requirements.txt
├── .gitignore
├── config.py
├── run_pipeline.py
├── src/
│   ├── __init__.py
│   ├── download_vnindex.py
│   ├── download_market_data.py
│   ├── pnj_gold_parser.py
│   ├── clean_data.py
│   └── calculate_returns.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── final/
└── notebooks/
```

Ba thư mục dữ liệu không lưu CSV trên GitHub. Khi pipeline được hoàn thiện, chúng sẽ lần lượt chứa dữ liệu gốc, dữ liệu đã làm sạch và ba bộ dữ liệu cuối dùng cho mô hình.

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Chạy pipeline

```bash
python3 run_pipeline.py
```

Repository hiện chứa bộ khung project, crawler PNJ và hai notebook nguồn. Logic trong notebook sẽ được tách dần sang các module trong `src/`.

