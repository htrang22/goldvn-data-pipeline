"""Cấu hình mặc định và đường dẫn dùng chung cho pipeline GoldVN."""

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
FINAL_DIR = PROJECT_DIR / "data" / "final"

START_DATE = "2023-08-01"
END_DATE = "2026-08-01"  # Ngày cuối cùng cần giữ, tính cả ngày này.

VNINDEX_SYMBOL = "VNINDEX"
VNINDEX_SOURCE = "KBS"
BTC_TICKER = "BTC-USD"
USDVND_TICKER = "VND=X"
GOLD_PRODUCT = "SJC"
GOLD_LOCATION = "TPHCM"

RAW_VNINDEX_FILE = RAW_DIR / "vnindex.csv"
RAW_BITCOIN_FILE = RAW_DIR / "bitcoin_usd.csv"
RAW_USDVND_FILE = RAW_DIR / "usdvnd.csv"
RAW_GOLD_FILE = RAW_DIR / "3y-sjc.csv"

CLEAN_VNINDEX_FILE = PROCESSED_DIR / "vnindex_clean.csv"
CLEAN_BITCOIN_FILE = PROCESSED_DIR / "bitcoin_usd_clean.csv"
CLEAN_USDVND_FILE = PROCESSED_DIR / "usdvnd_clean.csv"
CLEAN_GOLD_FILE = PROCESSED_DIR / "sjc_gold_clean.csv"

FINAL_BITCOIN_FILE = FINAL_DIR / "3y-bitcoin-vnd-returns.csv"
FINAL_GOLD_FILE = FINAL_DIR / "3y-gold-returns.csv"
FINAL_VNINDEX_FILE = FINAL_DIR / "3y-vnindex-returns.csv"


def ensure_data_directories() -> None:
    """Tạo các thư mục dữ liệu nếu chưa tồn tại."""

    for directory in (RAW_DIR, PROCESSED_DIR, FINAL_DIR):
        directory.mkdir(parents=True, exist_ok=True)
