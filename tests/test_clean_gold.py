import unittest
import tempfile
import shutil
from pathlib import Path

import pandas as pd

from src.clean_data import clean_gold


class TestCleanGold(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.output_path = self.tmpdir / "gold-clean-test.csv"

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_csv(self, filename: str, df: pd.DataFrame) -> Path:
        path = self.tmpdir / filename
        df.to_csv(path, index=False)
        return path

    # --- Schema 1: PNJ gốc (query_date, location, product, buy, sell) ---
    def test_pnj_schema(self):
        df = pd.DataFrame({
            "query_date": ["20240101", "20240102", "20240103"],
            "location": ["TPHCM", "TPHCM", "TPHCM"],
            "product": ["SJC", "SJC", "SJC"],
            "buy": [75000000, 75500000, 76000000],
            "sell": [76000000, 76500000, 77000000],
        })
        input_path = self._write_csv("pnj.csv", df)

        result = clean_gold(
            input_path, self.output_path,
            start_date="2024-01-01", end_date="2024-01-03",
        )

        self.assertEqual(len(result), 3)
        self.assertIn("gold_price", result.columns)
        # gold_price = (buy+sell)/2, kiểm tra dòng đầu
        self.assertAlmostEqual(result.iloc[0]["gold_price"], 75500000)
        self.assertTrue(self.output_path.exists())

    # --- Schema 2: người dùng tự cung cấp (Date, Buy, Sell) ---
    def test_date_buy_sell_schema(self):
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "Buy": [75000000, 75500000, 76000000],
            "Sell": [76000000, 76500000, 77000000],
        })
        input_path = self._write_csv("date_buy_sell.csv", df)

        result = clean_gold(
            input_path, self.output_path,
            start_date="2024-01-01", end_date="2024-01-03",
        )

        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(result.iloc[0]["gold_price"], 75500000)

    # --- Schema 3: chỉ có Date + Close ---
    def test_date_close_schema(self):
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "Close": [75800000, 76200000, 76900000],
        })
        input_path = self._write_csv("date_close.csv", df)

        result = clean_gold(
            input_path, self.output_path,
            start_date="2024-01-01", end_date="2024-01-03",
        )

        self.assertEqual(len(result), 3)
        # với schema close-only, gold_price phải bằng đúng close
        self.assertAlmostEqual(result.iloc[0]["gold_price"], 75800000)
        # buy/sell được gán = close nên sell >= buy luôn đúng, không bị lọc mất dòng nào
        self.assertTrue((result["buy"] == result["sell"]).all())

    # --- Trường hợp lỗi: thiếu cả buy/sell lẫn close ---
    def test_missing_price_columns_raises(self):
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02"],
            "Volume": [100, 200],
        })
        input_path = self._write_csv("invalid.csv", df)

        with self.assertRaises(ValueError):
            clean_gold(
                input_path, self.output_path,
                start_date="2024-01-01", end_date="2024-01-02",
            )

    # --- Trường hợp lỗi: file không đủ phủ khoảng ngày yêu cầu ---
    def test_insufficient_date_coverage_raises(self):
        df = pd.DataFrame({
            "Date": ["2024-01-01", "2024-01-02"],
            "Close": [75000000, 75500000],
        })
        input_path = self._write_csv("short_range.csv", df)

        with self.assertRaises(ValueError):
            clean_gold(
                input_path, self.output_path,
                start_date="2024-01-01", end_date="2024-06-01",  # vượt quá dữ liệu có
            )

    # --- Lọc TPHCM/SJC vẫn hoạt động khi có nhiều location/product khác ---
    def test_filters_non_tphcm_sjc_rows(self):
        df = pd.DataFrame({
            "query_date": ["20240101", "20240101", "20240102"],
            "location": ["TPHCM", "HaNoi", "TPHCM"],
            "product": ["SJC", "SJC", "SJC"],
            "buy": [75000000, 74000000, 75500000],
            "sell": [76000000, 75000000, 76500000],
        })
        input_path = self._write_csv("mixed_location.csv", df)

        result = clean_gold(
            input_path, self.output_path,
            start_date="2024-01-01", end_date="2024-01-02",
        )

        self.assertEqual(len(result), 2)  # chỉ giữ 2 dòng TPHCM


if __name__ == "__main__":
    unittest.main()