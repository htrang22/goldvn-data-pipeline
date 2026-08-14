from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.calculate_returns import (
    create_bitcoin_returns,
    create_gold_returns,
    create_vnindex_returns,
)
from src.clean_data import clean_bitcoin, clean_gold, clean_usdvnd, clean_vnindex
from src.download_market_data import download_bitcoin
from src.download_vnindex import download_vnindex


class PipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write(self, name: str, data: pd.DataFrame) -> Path:
        path = self.root / name
        data.to_csv(path, index=False)
        return path

    def test_cleaners_select_valid_rows_and_correct_gold_series(self) -> None:
        bitcoin_raw = self._write(
            "bitcoin.csv",
            pd.DataFrame(
                {
                    "Date": ["2023-08-01", "2023-08-02", "2023-08-03"],
                    "Open": [100, 110, 120],
                    "High": [115, 125, 100],
                    "Low": [95, 105, 110],
                    "Close": [110, 120, 115],
                    "Adj Close": [110, 120, 115],
                    "Volume": [10, 11, 12],
                }
            ),
        )
        fx_raw = self._write(
            "fx.csv",
            pd.DataFrame(
                {
                    "Date": ["2023-08-01", "2023-08-02"],
                    "Close": [23600, 23610],
                }
            ),
        )
        vnindex_raw = self._write(
            "vnindex.csv",
            pd.DataFrame(
                {
                    "time": ["2023-08-01", "2023-08-02"],
                    "close": [1217.56, 1220.43],
                }
            ),
        )
        gold_raw = self._write(
            "gold.csv",
            pd.DataFrame(
                {
                    "query_date": [20230801, 20230801, 20230802],
                    "location": ["TPHCM", "Hà Nội", "TPHCM"],
                    "product": ["SJC", "SJC", "SJC"],
                    "buy": [66600, 66500, 66700],
                    "sell": [67200, 67100, 67250],
                }
            ),
        )

        bitcoin = clean_bitcoin(
            bitcoin_raw, self.root / "bitcoin_clean.csv", "2023-08-01", "2023-08-03"
        )
        fx = clean_usdvnd(
            fx_raw, self.root / "fx_clean.csv", "2023-08-01", "2023-08-03"
        )
        vnindex = clean_vnindex(
            vnindex_raw,
            self.root / "vnindex_clean.csv",
            "2023-08-01",
            "2023-08-03",
        )
        gold = clean_gold(
            gold_raw,
            self.root / "gold_clean.csv",
            "2023-08-01",
            "2023-08-03",
        )

        self.assertEqual(len(bitcoin), 2)  # Dòng OHLC cuối không hợp lệ.
        self.assertEqual(len(fx), 2)
        self.assertEqual(len(vnindex), 2)
        self.assertEqual(gold["location"].unique().tolist(), ["TPHCM"])
        self.assertEqual(gold["gold_price"].tolist(), [66900.0, 66975.0])

    def test_returns_keep_btc_calendar_and_forward_fill_fx(self) -> None:
        bitcoin_path = self._write(
            "bitcoin_clean.csv",
            pd.DataFrame(
                {
                    "Date": ["2023-08-04", "2023-08-05", "2023-08-06"],
                    "btc_price": [100.0, 110.0, 121.0],
                }
            ),
        )
        fx_path = self._write(
            "fx_clean.csv",
            pd.DataFrame(
                {"Date": ["2023-08-04"], "usdvnd_rate": [24000.0]}
            ),
        )
        output = self.root / "btc_returns.csv"
        result = create_bitcoin_returns(bitcoin_path, fx_path, output)

        self.assertEqual(len(result), 3)
        self.assertEqual(result["fx_filled"].tolist(), [False, True, True])
        self.assertEqual(result["usdvnd_rate_used"].tolist(), [24000.0] * 3)
        self.assertAlmostEqual(result.loc[1, "btc_return"], 100 * np.log(1.1))
        self.assertTrue(output.exists())

    def test_clean_bitcoin_accepts_legacy_btc_price_column(self) -> None:
        legacy_path = self._write(
            "legacy_bitcoin.csv",
            pd.DataFrame(
                {
                    "Date": ["2023-08-01"],
                    "Open": [100.0],
                    "High": [110.0],
                    "Low": [90.0],
                    "btc_price": [105.0],
                }
            ),
        )
        cleaned = clean_bitcoin(
            legacy_path,
            self.root / "legacy_clean.csv",
            "2023-08-01",
            "2023-08-01",
        )

        self.assertEqual(cleaned.columns.tolist().count("btc_price"), 1)
        self.assertEqual(cleaned.loc[0, "btc_price"], 105.0)

    def test_gold_and_vnindex_returns_use_their_own_calendars(self) -> None:
        gold_path = self._write(
            "gold_clean.csv",
            pd.DataFrame(
                {
                    "Date": ["2023-08-04", "2023-08-07"],
                    "gold_price": [100.0, 102.0],
                }
            ),
        )
        vnindex_path = self._write(
            "vnindex_clean.csv",
            pd.DataFrame(
                {
                    "Date": ["2023-08-04", "2023-08-08"],
                    "vnindex_price": [1000.0, 1010.0],
                }
            ),
        )
        gold = create_gold_returns(gold_path, self.root / "gold_returns.csv")
        vnindex = create_vnindex_returns(
            vnindex_path, self.root / "vnindex_returns.csv"
        )

        self.assertEqual(gold["Date"].dt.strftime("%Y-%m-%d").tolist(), ["2023-08-04", "2023-08-07"])
        self.assertEqual(vnindex["Date"].dt.strftime("%Y-%m-%d").tolist(), ["2023-08-04", "2023-08-08"])
        self.assertAlmostEqual(gold.loc[1, "gold_return"], 100 * np.log(1.02))

    def test_yahoo_download_uses_exclusive_end_date(self) -> None:
        calls = {}

        def fake_download(**kwargs):
            calls.update(kwargs)
            frame = pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [110.0],
                    "Low": [90.0],
                    "Close": [105.0],
                },
                index=pd.DatetimeIndex(["2023-08-01"], name="Date"),
            )
            return frame

        fake_yfinance = SimpleNamespace(download=fake_download)
        output = self.root / "bitcoin_download.csv"
        with patch.dict("sys.modules", {"yfinance": fake_yfinance}):
            downloaded = download_bitcoin(
                output, "2023-08-01", "2023-08-01", ticker="BTC-USD"
            )

        self.assertEqual(calls["end"], "2023-08-02")
        self.assertEqual(calls["tickers"], "BTC-USD")
        self.assertEqual(len(downloaded), 1)
        self.assertTrue(output.exists())

    def test_vnindex_download_requests_one_extra_day(self) -> None:
        calls = {}

        class FakeQuote:
            def __init__(self, symbol, source):
                calls["init"] = (symbol, source)

            def history(self, **kwargs):
                calls.update(kwargs)
                return pd.DataFrame(
                    {"time": ["2023-08-01"], "close": [1217.56]}
                )

        output = self.root / "vnindex_download.csv"
        with patch.dict("sys.modules", {"vnstock": SimpleNamespace(Quote=FakeQuote)}):
            downloaded = download_vnindex(
                output,
                "2023-08-01",
                "2023-08-01",
                symbol="VNINDEX",
                source="KBS",
            )

        self.assertEqual(calls["init"], ("VNINDEX", "KBS"))
        self.assertEqual(calls["end"], "2023-08-02")
        self.assertEqual(len(downloaded), 1)
        self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
