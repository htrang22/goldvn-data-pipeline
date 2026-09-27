import pandas as pd
GOLD_COLUMN_ALIASES = {
    "date": ["query_date", "date", "Date", "ngay"],
    "buy": ["buy", "Buy", "buy_price", "gia_mua"],
    "sell": ["sell", "Sell", "sell_price", "gia_ban"],
    "close": ["close", "Close", "gia_dong_cua", "Adj Close", "adj_close"],
}

def normalize_gold_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {}
    for target, aliases in GOLD_COLUMN_ALIASES.items():
        for a in aliases:
            if a in df.columns:
                rename_map[a] = target
                break
    df = df.rename(columns=rename_map)

    if "date" not in df.columns:
        raise ValueError("Không tìm thấy cột ngày trong file vàng.")

    has_buy_sell = "buy" in df.columns and "sell" in df.columns
    has_close = "close" in df.columns
    if not has_buy_sell and not has_close:
        raise ValueError(
            "File vàng cần có cả 'buy' và 'sell', hoặc cột 'close', để tính gold_price."
        )

    if "location" not in df.columns:
        df["location"] = None
    if "product" not in df.columns:
        df["product"] = None

    return df

def compute_gold_price(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "buy" in df.columns and "sell" in df.columns and df["buy"].notna().any():
        df["gold_price"] = (df["buy"] + df["sell"]) / 2
    elif "close" in df.columns:
        df["gold_price"] = df["close"]
        # để các bước lọc buy>0/sell>0/sell>=buy phía sau vẫn chạy được không lỗi
        df["buy"] = df["close"]
        df["sell"] = df["close"]
    else:
        raise ValueError("Không đủ dữ liệu để tính gold_price.")
    return df