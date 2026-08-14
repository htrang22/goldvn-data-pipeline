"""Điểm chạy chính của pipeline dữ liệu GoldVN."""

from __future__ import annotations

import argparse
from datetime import date

from config import (
    BTC_TICKER,
    CLEAN_BITCOIN_FILE,
    CLEAN_GOLD_FILE,
    CLEAN_USDVND_FILE,
    CLEAN_VNINDEX_FILE,
    END_DATE,
    FINAL_BITCOIN_FILE,
    FINAL_GOLD_FILE,
    FINAL_VNINDEX_FILE,
    GOLD_LOCATION,
    GOLD_PRODUCT,
    RAW_BITCOIN_FILE,
    RAW_GOLD_FILE,
    RAW_USDVND_FILE,
    RAW_VNINDEX_FILE,
    START_DATE,
    USDVND_TICKER,
    VNINDEX_SOURCE,
    VNINDEX_SYMBOL,
    ensure_data_directories,
)
from src.calculate_returns import (
    create_bitcoin_returns,
    create_gold_returns,
    create_vnindex_returns,
)
from src.clean_data import clean_bitcoin, clean_gold, clean_usdvnd, clean_vnindex
from src.download_market_data import download_bitcoin, download_usdvnd
from src.download_vnindex import download_vnindex


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tải, làm sạch và tính return cho dữ liệu GoldVN."
    )
    parser.add_argument("--start-date", default=START_DATE)
    parser.add_argument("--end-date", default=END_DATE)
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Không tải lại; dùng bốn CSV hiện có trong data/raw.",
    )
    return parser


def download_all(
    start_date: str,
    end_date: str,
) -> None:
    """Tải ba chuỗi online; giá vàng luôn do người dùng cung cấp qua CSV."""

    print("[1/3] Tải VN-Index...")
    download_vnindex(
        RAW_VNINDEX_FILE,
        start_date,
        end_date,
        symbol=VNINDEX_SYMBOL,
        source=VNINDEX_SOURCE,
    )
    print("[2/3] Tải BTC-USD...")
    download_bitcoin(
        RAW_BITCOIN_FILE, start_date, end_date, ticker=BTC_TICKER
    )
    print("[3/3] Tải USD/VND...")
    download_usdvnd(
        RAW_USDVND_FILE, start_date, end_date, ticker=USDVND_TICKER
    )


def process_all(start_date: str, end_date: str) -> None:
    missing_inputs = [
        path
        for path in [
            RAW_BITCOIN_FILE,
            RAW_USDVND_FILE,
            RAW_VNINDEX_FILE,
            RAW_GOLD_FILE,
        ]
        if not path.exists()
    ]
    if missing_inputs:
        formatted = "\n".join(f"- {path}" for path in missing_inputs)
        raise FileNotFoundError(
            "Thiếu file đầu vào trong data/raw:\n" + formatted
        )

    print("Làm sạch dữ liệu...")
    clean_bitcoin(
        RAW_BITCOIN_FILE, CLEAN_BITCOIN_FILE, start_date, end_date
    )
    clean_usdvnd(RAW_USDVND_FILE, CLEAN_USDVND_FILE, start_date, end_date)
    clean_vnindex(
        RAW_VNINDEX_FILE, CLEAN_VNINDEX_FILE, start_date, end_date
    )
    clean_gold(
        RAW_GOLD_FILE,
        CLEAN_GOLD_FILE,
        start_date,
        end_date,
        product=GOLD_PRODUCT,
        location=GOLD_LOCATION,
    )

    print("Quy đổi BTC sang VND và tính log-return...")
    bitcoin = create_bitcoin_returns(
        CLEAN_BITCOIN_FILE, CLEAN_USDVND_FILE, FINAL_BITCOIN_FILE
    )
    gold = create_gold_returns(CLEAN_GOLD_FILE, FINAL_GOLD_FILE)
    vnindex = create_vnindex_returns(CLEAN_VNINDEX_FILE, FINAL_VNINDEX_FILE)

    print("\nHoàn thành:")
    print(f"- BTC-VND: {len(bitcoin):,} dòng -> {FINAL_BITCOIN_FILE}")
    print(f"- Vàng SJC: {len(gold):,} dòng -> {FINAL_GOLD_FILE}")
    print(f"- VN-Index: {len(vnindex):,} dòng -> {FINAL_VNINDEX_FILE}")


def main() -> None:
    """Chạy tuần tự toàn bộ pipeline."""

    args = build_parser().parse_args()
    try:
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
    except ValueError as exc:
        raise ValueError("Ngày phải có định dạng YYYY-MM-DD.") from exc
    if start_date > end_date:
        raise ValueError("--start-date phải nhỏ hơn hoặc bằng --end-date.")
    ensure_data_directories()
    if not RAW_GOLD_FILE.exists():
        raise FileNotFoundError(
            "Hãy đặt file giá vàng đã tải vào "
            f"{RAW_GOLD_FILE} trước khi chạy pipeline. "
            "Crawler PNJ trong src/ chỉ là công cụ tham chiếu và không được chạy tự động."
        )
    if not args.skip_download:
        download_all(args.start_date, args.end_date)
    process_all(args.start_date, args.end_date)


if __name__ == "__main__":
    main()
