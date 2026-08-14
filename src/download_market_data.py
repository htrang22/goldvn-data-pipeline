"""Tải BTC-USD và USD/VND từ Yahoo Finance."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd


PathLike = Union[str, Path]


def _download_yahoo(
    ticker: str,
    output_path: PathLike,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Tải một chuỗi ngày từ Yahoo Finance và lưu dạng CSV phẳng."""

    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài yfinance. Hãy chạy: python3 -m pip install -r requirements.txt"
        ) from exc

    exclusive_end = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    data = yf.download(
        tickers=ticker,
        start=start_date,
        end=exclusive_end,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )

    if data.empty:
        raise RuntimeError(f"Không tải được dữ liệu {ticker} từ Yahoo Finance.")

    data = data.reset_index()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.loc[:, ~data.columns.duplicated()].copy()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, date_format="%Y-%m-%d")
    return data


def download_bitcoin(
    output_path: PathLike,
    start_date: str,
    end_date: str,
    ticker: str = "BTC-USD",
) -> pd.DataFrame:
    """Tải giá Bitcoin theo USD."""

    return _download_yahoo(ticker, output_path, start_date, end_date)


def download_usdvnd(
    output_path: PathLike,
    start_date: str,
    end_date: str,
    ticker: str = "VND=X",
) -> pd.DataFrame:
    """Tải tỷ giá USD/VND."""

    return _download_yahoo(ticker, output_path, start_date, end_date)
