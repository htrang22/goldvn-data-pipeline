"""Tải dữ liệu VN-Index từ nguồn KBS thông qua vnstock."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd


PathLike = Union[str, Path]


def download_vnindex(
    output_path: PathLike,
    start_date: str,
    end_date: str,
    symbol: str = "VNINDEX",
    source: str = "KBS",
) -> pd.DataFrame:
    """Tải VN-Index và lưu nguyên bản vào ``output_path``.

    ``end_date`` là ngày cuối cùng cần lấy. Hàm cộng thêm một ngày khi gọi
    nguồn dữ liệu để tránh phụ thuộc vào cách diễn giải ngày kết thúc.
    """

    try:
        from vnstock import Quote
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài vnstock. Hãy chạy: python3 -m pip install -r requirements.txt"
        ) from exc

    source_end = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    quote = Quote(symbol=symbol, source=source)
    data = quote.history(
        symbol=symbol,
        start=start_date,
        end=source_end,
        interval="1D",
    )

    if data is None or data.empty:
        raise RuntimeError(f"Không tải được {symbol} từ nguồn {source}.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, encoding="utf-8-sig")
    return data
