"""Quy đổi BTC sang VND và tính log-return cho từng tài sản."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd


PathLike = Union[str, Path]


def _read_clean(path: PathLike, price_column: str, label: str) -> pd.DataFrame:
    data = pd.read_csv(path, parse_dates=["Date"])
    required = {"Date", price_column}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"{label} thiếu các cột bắt buộc: {missing}")

    data = data.sort_values("Date").reset_index(drop=True)
    if data["Date"].duplicated().any():
        raise ValueError(f"{label} có ngày bị trùng.")
    if data[price_column].isna().any() or (data[price_column] <= 0).any():
        raise ValueError(f"{label} có giá thiếu hoặc không dương.")
    return data


def _save(data: pd.DataFrame, output_path: PathLike) -> pd.DataFrame:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, date_format="%Y-%m-%d")
    return data


def create_bitcoin_returns(
    bitcoin_path: PathLike,
    usdvnd_path: PathLike,
    output_path: PathLike,
) -> pd.DataFrame:
    """Giữ lịch BTC, forward-fill tỷ giá và tính BTC-VND log-return."""

    bitcoin = _read_clean(bitcoin_path, "btc_price", "BTC")
    fx = _read_clean(usdvnd_path, "usdvnd_rate", "USD/VND")
    result = bitcoin.merge(
        fx[["Date", "usdvnd_rate"]],
        on="Date",
        how="left",
        validate="one_to_one",
    )
    if len(result) != len(bitcoin) or not result["Date"].equals(bitcoin["Date"]):
        raise AssertionError("Lịch BTC đã thay đổi khi ghép tỷ giá.")

    result["fx_observed"] = result["usdvnd_rate"].notna()
    result["usdvnd_rate_used"] = result["usdvnd_rate"].ffill()
    if result["usdvnd_rate_used"].isna().any():
        first_date = result.loc[
            result["usdvnd_rate_used"].isna(), "Date"
        ].min()
        raise ValueError(
            "Không có tỷ giá để forward-fill từ đầu chuỗi BTC. "
            f"Ngày đầu bị thiếu: {first_date:%Y-%m-%d}."
        )

    result["btc_vnd_price"] = result["btc_price"] * result["usdvnd_rate_used"]
    result["btc_return"] = 100 * np.log(
        result["btc_vnd_price"] / result["btc_vnd_price"].shift(1)
    )
    result["btc_usd_return"] = 100 * np.log(
        result["btc_price"] / result["btc_price"].shift(1)
    )
    result["fx_filled"] = ~result["fx_observed"]
    return _save(result, output_path)


def create_gold_returns(
    gold_path: PathLike, output_path: PathLike
) -> pd.DataFrame:
    """Tính log-return vàng trên lịch quan sát riêng của vàng."""

    gold = _read_clean(gold_path, "gold_price", "Vàng")
    gold["gold_return"] = 100 * np.log(
        gold["gold_price"] / gold["gold_price"].shift(1)
    )
    return _save(gold, output_path)


def create_vnindex_returns(
    vnindex_path: PathLike, output_path: PathLike
) -> pd.DataFrame:
    """Tính log-return VN-Index trên lịch giao dịch của chỉ số."""

    vnindex = _read_clean(vnindex_path, "vnindex_price", "VN-Index")
    vnindex["vnindex_return"] = 100 * np.log(
        vnindex["vnindex_price"] / vnindex["vnindex_price"].shift(1)
    )
    return _save(vnindex, output_path)
