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
| Vàng | File CSV do người dùng cung cấp | SJC, TPHCM (hoặc dữ liệu tự chuẩn bị khác, xem bên dưới) |

## Dự án sử dụng dữ liệu đầu ra

Ba dataset cuối do pipeline tạo ra được sử dụng trong dự án:

- [btc-sjc-vnindex-risk-analysis](https://github.com/htrang22/btc-sjc-vnindex-risk-analysis)

Repository trên thực hiện phân tích ARMA-EGARCH, DCC-GARCH và
Diebold-Yılmaz đối với Bitcoin, vàng SJC và VN-Index.

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
│   ├── gold_normalizer.py
│   ├── clean_data.py
│   └── calculate_returns.py
│   └── manifest.py
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── final/
└── tests/
```

4 thư mục dữ liệu không lưu CSV trên GitHub (ngoại trừ `data/final/run_manifest.json`, xem mục "Manifest" bên dưới). Khi chạy pipeline, chúng lần lượt chứa dữ liệu gốc, dữ liệu đã làm sạch và ba bộ dữ liệu cuối dùng cho mô hình.

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```
**Lưu ý:** `vnstock` không nằm trên PyPI mặc định. `requirements.txt` đã có sẵn dòng `--extra-index-url https://vnstocks.com/api/simple`, nên chỉ cần chạy đúng lệnh `pip install -r requirements.txt` ở trên là đủ, không cần cài `vnstock` riêng.

## Chạy pipeline

Trước tiên, đặt file CSV giá vàng đã tải vào:

```text
data/raw/sjc.csv
```
File này chấp nhận 1 trong 3 định dạng cột:

| Schema | Cột |
| --- | --- |
| PNJ gốc | `query_date`, `location`, `product`, `buy`, `sell` |
| Tự chuẩn bị (buy/sell) | `Date`, `Buy`, `Sell` |
| Tự chuẩn bị (chỉ giá đóng cửa) | `Date`, `Close` |

Nếu dùng schema có `buy`/`sell`, `gold_price` được tính bằng `(buy + sell) / 2`.
Nếu chỉ có `Close`, `gold_price` = `Close`. Nếu file có cột `location`/`product`, pipeline sẽ lọc đúng theo tham số `--gold-location`/`--gold-product` (mặc định `TPHCM`/`SJC`); nếu không có 2 cột này, bước lọc được bỏ qua.

Sau đó tải VN-Index, BTC-USD, USD/VND và xử lý cả 4 chuỗi:

```bash
python3 run_pipeline.py
```

Pipeline không tự động gọi crawler PNJ. File `src/pnj_gold_parser.py` chỉ được giữ làm căn cứ về nguồn dữ liệu và là công cụ tùy chọn cho người muốn tự crawl. Cách này tránh làm quy trình chính phụ thuộc vào API hoặc giao diện PNJ có thể thay đổi theo thời gian.

## Ghi nhận đóng góp

`src/pnj_gold_parser.py` được kế thừa từ file ban đầu `pnj_gold.py`, hình thành nhờ sự hỗ trợ ban đầu của anh **Thanh NT** ([GitHub: @ysoseriouz](https://github.com/ysoseriouz)). Từ nền tảng đó, **Nguyễn * Huệ Trang** tiếp tục chỉnh sửa và phát triển crawler để phù hợp với phạm vi, cấu trúc và yêu cầu dữ liệu của dự án GoldVN.

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
| `sjc.csv` | Xem bảng 3 schema ở mục "Chạy pipeline" phía trên |


Có thể thay khoảng ngày mặc định:

```bash
python3 run_pipeline.py --start-date 2023-08-01 --end-date 2026-08-01
```

> **Lưu ý về khoảng ngày:** `run_pipeline.py` chỉ tự tải VN-Index, BTC-USD và USD/VND. Dữ liệu vàng luôn được đọc từ file có sẵn `data/raw/3y-sjc.csv`, sau đó được lọc theo `--start-date` và `--end-date`. Vì vậy, file CSV vàng phải bao phủ toàn bộ khoảng ngày cần nghiên cứu trước khi chạy. Nếu mở rộng khoảng ngày nhưng không thay file vàng tương ứng, pipeline sẽ không thể tạo thêm quan sát vàng cho phần thời gian còn thiếu.

## Kết quả

Pipeline tạo ba file trong `data/final/`:

- `bitcoin-vnd-returns.csv`
- `gold-returns.csv`
- `vnindex-returns.csv`

BTC giữ nguyên lịch giao dịch hằng ngày. Tỷ giá USD/VND thiếu vào cuối tuần hoặc ngày nghỉ được forward-fill từ quan sát gần nhất. Vàng và VN-Index được tính return trên lịch quan sát riêng; không inner-join ba chuỗi trước khi tính return.

## Manifest

Mỗi lần chạy `run_pipeline.py` thành công, một file `data/final/run_manifest.json` được tạo (hoặc ghi đè), lưu lại:
- Thời điểm chạy (UTC).
- `--start-date`/`--end-date` đã dùng.
- SHA256 và thời điểm chỉnh sửa của từng file trong `data/raw/`.
- SHA256 của từng file kết quả trong `data/final/`.

File này giúp xác định chính xác dữ liệu đầu vào nào đã tạo ra một bộ kết quả cụ thể, kể cả khi `data/raw/` sau đó bị ghi đè bởi lần chạy khác.

## Kiểm thử

```bash
python3 -m unittest discover -v
```
`tests/test_clean_gold.py` kiểm tra hàm `clean_gold()` với cả 3 schema vàng (PNJ gốc, `Date+Buy+Sell`, `Date+Close`), cùng các trường hợp lỗi (thiếu cột giá, dữ liệu không đủ phủ khoảng ngày yêu cầu).

## Lưu ý về dữ liệu và quyền sử dụng

Repository này không lưu trữ hoặc phân phối file CSV chứa dữ liệu lịch sử giá vàng được thu thập từ nguồn của PNJ. Người dùng phải tự chuẩn bị file dữ liệu đầu vào và đặt tại `data/raw/3y-sjc.csv` để chạy pipeline.

Thông tin giá vàng được tham chiếu từ dữ liệu công khai của PNJ. Tên PNJ, nhãn hiệu và các quyền liên quan thuộc về chủ sở hữu tương ứng. Dự án này không được PNJ tài trợ, chứng thực hoặc liên kết chính thức.

Chủ dự án chưa nhận được giấy phép hoặc văn bản xác nhận từ PNJ cho phép tái phân phối bộ dữ liệu lịch sử giá vàng. Việc cung cấp mã crawler trong repository chỉ nhằm mục đích tham khảo kỹ thuật và ghi nhận phương pháp hình thành dataset; mã nguồn này không cấu thành sự cho phép thu thập, sao chép hoặc tái phân phối dữ liệu từ bất kỳ nguồn nào.

Người sử dụng có trách nhiệm tự bảo đảm việc thu thập và sử dụng dữ liệu tuân thủ điều khoản của nguồn dữ liệu, quy định về quyền sở hữu trí tuệ và pháp luật áp dụng. Mọi giấy phép của repository, nếu có, chỉ áp dụng cho mã nguồn và tài liệu do tác giả dự án tạo ra, không áp dụng cho dữ liệu hoặc tài sản thuộc bên thứ ba.

Dữ liệu và kết quả xử lý được cung cấp cho mục đích nghiên cứu, không bảo đảm tuyệt đối về tính chính xác, đầy đủ hoặc cập nhật và không cấu thành khuyến nghị đầu tư.
