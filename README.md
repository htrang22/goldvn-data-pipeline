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
├── notebooks/
└── tests/
```

Ba thư mục dữ liệu không lưu CSV trên GitHub. Khi chạy pipeline, chúng lần lượt chứa dữ liệu gốc, dữ liệu đã làm sạch và ba bộ dữ liệu cuối dùng cho mô hình.

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Chạy pipeline

Tải lại toàn bộ dữ liệu và xử lý:

```bash
python3 run_pipeline.py
```

Crawler PNJ hỗ trợ tiếp tục từ file đang có. Quá trình tải ba năm dữ liệu vàng có delay giữa các request nên sẽ mất thời gian; không xóa `data/raw/sjc_gold.csv` nếu muốn tiếp tục lần chạy trước.

Nếu bốn file raw đã có sẵn, chỉ làm sạch và tính return:

```bash
python3 run_pipeline.py --skip-download
```

Bốn file cần có trong `data/raw/` khi dùng `--skip-download`:

| File | Cột bắt buộc |
| --- | --- |
| `vnindex.csv` | `time`, `close` (hoặc `Date`, `vnindex_price`) |
| `bitcoin_usd.csv` | `Date`, `Open`, `High`, `Low`, `Close` (chấp nhận `btc_price`) |
| `usdvnd.csv` | `Date`, `Close` (chấp nhận `usdvnd_rate`) |
| `sjc_gold.csv` | `query_date`, `location`, `product`, `buy`, `sell` |

Có thể thay khoảng ngày mặc định:

```bash
python3 run_pipeline.py --start-date 2023-08-01 --end-date 2026-08-01
```

## Kết quả

Pipeline tạo ba file trong `data/final/`:

- `3y-bitcoin-vnd-returns.csv`
- `3y-gold-returns.csv`
- `3y-vnindex-returns.csv`

BTC giữ nguyên lịch giao dịch hằng ngày. Tỷ giá USD/VND thiếu vào cuối tuần hoặc ngày nghỉ được forward-fill từ quan sát gần nhất. Vàng và VN-Index được tính return trên lịch quan sát riêng; không inner-join ba chuỗi trước khi tính return.

## Kiểm thử

```bash
python3 -m unittest discover -v
```

Hai notebook trong `notebooks/` được giữ làm tài liệu đối chiếu; pipeline chính nằm trong các module Python ở `src/`.
