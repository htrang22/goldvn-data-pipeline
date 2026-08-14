"""Làm sạch và chuẩn hóa các chuỗi giá theo ngày."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union

import numpy as np
import pandas as pd


PathLike = Union[str, Path]


def _require_columns(data: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"{label} thiếu các cột bắt buộc: {missing}")


def _normalize_dates(values: pd.Series) -> pd.Series:
    return (
        pd.to_datetime(values, errors="coerce", utc=True)
        .dt.tz_localize(None)
        .dt.normalize()
    )


def _limit_date_range(
    data: pd.DataFrame, start_date: str, end_date: str
) -> pd.DataFrame:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    return data.loc[data["Date"].between(start, end)].copy()


def _save_clean(data: pd.DataFrame, output_path: PathLike) -> pd.DataFrame:
    if data.empty:
        raise ValueError("Không còn quan sát hợp lệ sau khi làm sạch.")
    if data["Date"].duplicated().any():
        raise ValueError("Dữ liệu sau làm sạch vẫn còn ngày bị trùng.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, date_format="%Y-%m-%d")
    return data


def clean_bitcoin(
    input_path: PathLike,
    output_path: PathLike,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Chuẩn hóa BTC-USD và kiểm tra tính nhất quán của OHLC."""

    data = pd.read_csv(input_path)
    if "Close" not in data and "btc_price" in data:
        data = data.rename(columns={"btc_price": "Close"})
    _require_columns(data, ["Date", "Open", "High", "Low", "Close"], "BTC")

    data["Date"] = _normalize_dates(data["Date"])
    numeric_columns = ["Open", "High", "Low", "Close"]
    optional_numeric = [column for column in ["Adj Close", "Volume"] if column in data]
    for column in numeric_columns + optional_numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["Date"] + numeric_columns).copy()
    data = data.loc[data[numeric_columns].gt(0).all(axis=1)].copy()
    valid_ohlc = (
        (data["High"] >= data[["Open", "Low", "Close"]].max(axis=1))
        & (data["Low"] <= data[["Open", "High", "Close"]].min(axis=1))
    )
    data = data.loc[valid_ohlc].copy()

    if "Volume" in data:
        data.loc[data["Volume"] < 0, "Volume"] = np.nan

    data = _limit_date_range(data, start_date, end_date)
    data = (
        data.sort_values("Date")
        .drop_duplicates(subset="Date", keep="last")
        .reset_index(drop=True)
    )
    data = data.rename(columns={"Close": "btc_price"})

    selected = ["Date", "Open", "High", "Low", "btc_price"]
    selected.extend(column for column in ["Adj Close", "Volume"] if column in data)
    data = data[selected].copy()
    data["day_gap"] = data["Date"].diff().dt.days
    return _save_clean(data, output_path)


def clean_usdvnd(
    input_path: PathLike,
    output_path: PathLike,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Chuẩn hóa tỷ giá USD/VND từ Yahoo Finance."""

    data = pd.read_csv(input_path)
    if "Close" not in data and "usdvnd_rate" in data:
        data["Close"] = data["usdvnd_rate"]
    _require_columns(data, ["Date", "Close"], "USD/VND")
    data["Date"] = _normalize_dates(data["Date"])
    data["usdvnd_rate"] = pd.to_numeric(data["Close"], errors="coerce")
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["Date", "usdvnd_rate"])
    data = data.loc[data["usdvnd_rate"] > 0, ["Date", "usdvnd_rate"]]
    data = _limit_date_range(data, start_date, end_date)
    data = (
        data.sort_values("Date")
        .drop_duplicates(subset="Date", keep="last")
        .reset_index(drop=True)
    )
    return _save_clean(data, output_path)


def clean_vnindex(
    input_path: PathLike,
    output_path: PathLike,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Chuẩn hóa ngày và giá đóng cửa VN-Index."""

    data = pd.read_csv(input_path)
    if {"time", "close"}.issubset(data.columns):
        date_column = "time"
        price_column = "close"
    elif {"Date", "vnindex_price"}.issubset(data.columns):
        date_column = "Date"
        price_column = "vnindex_price"
    else:
        raise ValueError(
            "VN-Index cần cặp cột time/close hoặc Date/vnindex_price."
        )
    data["Date"] = _normalize_dates(data[date_column])
    data["vnindex_price"] = pd.to_numeric(data[price_column], errors="coerce")
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["Date", "vnindex_price"])
    data = data.loc[data["vnindex_price"] > 0, ["Date", "vnindex_price"]]
    data = _limit_date_range(data, start_date, end_date)
    data = (
        data.sort_values("Date")
        .drop_duplicates(subset="Date", keep="last")
        .reset_index(drop=True)
    )
    return _save_clean(data, output_path)


def clean_gold(
    input_path: PathLike,
    output_path: PathLike,
    start_date: str,
    end_date: str,
    product: str = "SJC",
    location: str = "TPHCM",
) -> pd.DataFrame:
    """Lọc đúng SJC/TPHCM và tính midpoint từ giá mua, giá bán."""

    data = pd.read_csv(input_path)
    _require_columns(
        data,
        ["query_date", "location", "product", "buy", "sell"],
        "Vàng",
    )
    data = data.loc[
        data["product"].eq(product) & data["location"].eq(location)
    ].copy()
    if data.empty:
        raise ValueError(
            f"Không tìm thấy dữ liệu vàng product={product!r}, location={location!r}."
        )

    query_dates = data["query_date"].astype(str).str.replace(".0", "", regex=False)
    data["Date"] = pd.to_datetime(
        query_dates, format="%Y%m%d", errors="coerce"
    )
    for column in ["buy", "sell"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["Date", "buy", "sell"])
    data = data.loc[
        (data["buy"] > 0) & (data["sell"] > 0) & (data["sell"] >= data["buy"])
    ].copy()
    data = _limit_date_range(data, start_date, end_date)

    sort_columns = ["Date"]
    for column in ["updated_at", "crawl_time"]:
        if column in data:
            data[column] = pd.to_datetime(data[column], errors="coerce")
            sort_columns.append(column)
    data = data.sort_values(sort_columns, kind="stable")
    data = data.drop_duplicates(subset="Date", keep="last").reset_index(drop=True)
    data["gold_price"] = (data["buy"] + data["sell"]) / 2
    data = data[["Date", "location", "product", "buy", "sell", "gold_price"]]
    return _save_clean(data, output_path)
