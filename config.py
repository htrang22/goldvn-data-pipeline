"""Cấu hình dùng chung cho pipeline dữ liệu GoldVN."""

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
FINAL_DIR = PROJECT_DIR / "data" / "final"

START_DATE = "2023-08-01"
YAHOO_END_DATE = "2026-08-02"  # Yahoo Finance không bao gồm ngày end.
PNJ_END_DATE = "2026-08-01"  # Crawler PNJ bao gồm ngày kết thúc.

VNINDEX_SYMBOL = "VNINDEX"
VNINDEX_SOURCE = "KBS"
BTC_TICKER = "BTC-USD"
USDVND_TICKER = "VND=X"
GOLD_PRODUCT = "sjc"
GOLD_LOCATION = "hcm"


def ensure_data_directories() -> None:
    """Tạo các thư mục dữ liệu nếu chưa tồn tại."""

    for directory in (RAW_DIR, PROCESSED_DIR, FINAL_DIR):
        directory.mkdir(parents=True, exist_ok=True)

