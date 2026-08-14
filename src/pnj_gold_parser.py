#!/usr/bin/env python3
"""
PNJ Gold Price Crawler

Ghi nhận:
- File này được kế thừa từ parser ban đầu `pnj_gold.py`, hình thành nhờ
  sự hỗ trợ ban đầu của anh Nguyễn Tiến Thành
  (GitHub: https://github.com/ysoseriouz).
- Nguyễn * Huệ Trang tiếp tục chỉnh sửa và phát triển để phù hợp với phạm vi,
  cấu trúc và yêu cầu dữ liệu của dự án GoldVN.

Chức năng chính:
- Gọi API lịch sử giá vàng PNJ.
- Parse dữ liệu theo ngày.
- Chuẩn hóa giá mua / bán.
- Lọc theo sản phẩm và khu vực.
- Lưu toàn bộ lịch sử hoặc chỉ snapshot cuối ngày.
- Hỗ trợ resume, retry và delay giữa các request.

Tương thích: Python 3.8+
"""

from __future__ import annotations

import argparse
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import pandas as pd
import requests
from tqdm import tqdm

API_URL = (
    "https://edge-cf-api.pnj.io/"
    "ecom-frontend/v1/get-gold-price-history"
)

HEADERS = {
    "Accept": "application/json",
    "Origin": "https://giavang.pnj.com.vn",
    "Referer": "https://giavang.pnj.com.vn/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

PRODUCTS: Dict[str, str] = {
    "pnj": "PNJ",
    "sjc": "SJC",
    "ring9999": "Nhẫn Trơn PNJ 999.9",
    "kimbao": "Vàng Kim Bảo 999.9",
    "phucloctai": "Vàng Phúc Lộc Tài 999.9",
    "9999": "Vàng nữ trang 999.9",
    "999": "Vàng nữ trang 999",
    "9920": "Vàng nữ trang 9920",
    "99": "Vàng nữ trang 99",
    "22k": "Vàng 916 (22K)",
    "18k": "Vàng 750 (18K)",
    "16k": "Vàng 680 (16.3K)",
    "15k": "Vàng 650 (15.6K)",
    "14k6": "Vàng 610 (14.6K)",
    "14k": "Vàng 585 (14K)",
    "10k": "Vàng 416 (10K)",
    "9k": "Vàng 375 (9K)",
    "8k": "Vàng 333 (8K)",
    "raw9999": "99.99",
    "raw99": "99",
}

LOCATIONS: Dict[str, str] = {
    "hcm": "TPHCM",
    "hn": "Hà Nội",
    "dn": "Đà Nẵng",
    "mt": "Miền Tây",
    "tn": "Tây Nguyên",
    "dnb": "Đông Nam Bộ",
    "jewelry": "Giá vàng nữ trang",
    "raw": "Nguyên liệu mua ngoài",
}

SUPPORTED_UPDATED_AT_FORMATS: Sequence[str] = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d/%m/%y %H:%M",
)


def generate_dates(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: Optional[int] = None,
) -> List[str]:
    """Tạo danh sách ngày theo định dạng YYYYMMDD."""

    if bool(start_date) != bool(end_date):
        raise ValueError(
            "Phải truyền đồng thời --start-date và --end-date."
        )

    if start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if start > end:
            raise ValueError(
                "--start-date phải nhỏ hơn hoặc bằng --end-date."
            )

        result: List[str] = []
        current = start

        while current <= end:
            result.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)

        return result

    number_of_days = 180 if days is None else days

    if number_of_days <= 0:
        raise ValueError("--days phải lớn hơn 0.")

    today = datetime.now()

    return [
        (today - timedelta(days=i)).strftime("%Y%m%d")
        for i in range(number_of_days)
    ]


def normalize_price(value: Any) -> Optional[int]:
    """Chuyển giá từ chuỗi như 137.500 hoặc 137,500 thành int."""

    if value is None or pd.isna(value):
        return None

    normalized = (
        str(value)
        .replace(".", "")
        .replace(",", "")
        .strip()
    )

    if not normalized:
        return None

    return int(normalized)


def parse_updated_at(value: Any) -> pd.Timestamp:
    """Parse updated_at từ nhiều định dạng ngày giờ PNJ có thể trả về."""

    if value is None or str(value).strip() == "":
        return pd.NaT

    text = str(value).strip()

    for fmt in SUPPORTED_UPDATED_AT_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(text, fmt))
        except ValueError:
            continue

    return pd.to_datetime(text, errors="coerce", dayfirst=True)


def parse_keywords(
    raw_value: Optional[str],
    mapping: Dict[str, str],
    label: str,
) -> Optional[Set[str]]:
    """Chuyển danh sách keyword CLI thành tập tên đầy đủ."""

    if not raw_value:
        return None

    selected: Set[str] = set()

    for keyword in raw_value.split(","):
        key = keyword.strip().lower()

        if key not in mapping:
            valid = ", ".join(sorted(mapping))
            raise ValueError(
                "%s không hợp lệ: %s. Giá trị hợp lệ: %s"
                % (label, key, valid)
            )

        selected.add(mapping[key])

    return selected


class PNJGoldCrawler:
    """Crawler và parser dữ liệu giá vàng PNJ."""

    def __init__(
        self,
        output: str,
        mode: str = "snapshot",
        products: Optional[Set[str]] = None,
        locations: Optional[Set[str]] = None,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        retries: int = 5,
        timeout: int = 30,
    ) -> None:
        if mode not in {"history", "snapshot"}:
            raise ValueError("mode phải là 'history' hoặc 'snapshot'.")

        if min_delay < 0 or max_delay < min_delay:
            raise ValueError("Khoảng delay không hợp lệ.")

        self.output = Path(output)
        self.mode = mode
        self.products = products
        self.locations = locations
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.retries = retries
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        self.rows: List[Dict[str, Any]] = []
        self.completed_dates: Set[str] = set()

        self._load_existing()

    def _load_existing(self) -> None:
        """Đọc file hiện có để hỗ trợ resume."""

        if not self.output.exists():
            return

        try:
            if self.output.suffix.lower() == ".parquet":
                df = pd.read_parquet(self.output)
            else:
                df = pd.read_csv(self.output)

            if df.empty:
                return

            self.rows = df.to_dict("records")

            if "query_date" in df.columns:
                self.completed_dates = set(
                    df["query_date"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                    .tolist()
                )

            logging.info(
                "Đã nạp %d dòng dữ liệu hiện có.",
                len(self.rows),
            )

        except Exception as exc:
            logging.warning(
                "Không thể đọc file hiện có: %s",
                exc,
            )

    def fetch(self, query_date: str) -> Optional[Dict[str, Any]]:
        """Gọi API cho một ngày, có retry và exponential backoff."""

        for attempt in range(self.retries):
            try:
                response = self.session.get(
                    API_URL,
                    params={"date": query_date},
                    timeout=self.timeout,
                )

                if response.status_code == 429:
                    raise RuntimeError("API giới hạn tần suất request.")

                response.raise_for_status()
                payload = response.json()

                if not isinstance(payload, dict):
                    raise ValueError("API không trả về JSON object hợp lệ.")

                return payload

            except Exception as exc:
                wait = (2 ** attempt) + random.uniform(0, 1)

                logging.warning(
                    "Request ngày %s thất bại: %s. "
                    "Thử lại %d/%d sau %.1f giây.",
                    query_date,
                    exc,
                    attempt + 1,
                    self.retries,
                    wait,
                )

                time.sleep(wait)

        logging.error("Không tải được dữ liệu ngày %s.", query_date)
        return None

    def parse(
        self,
        query_date: str,
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Parse payload API thành danh sách record giá vàng."""

        records: List[Dict[str, Any]] = []
        crawl_time = datetime.now()
        source_order = 0

        for location in payload.get("locations", []):
            location_name = location.get("name")

            if not location_name:
                continue

            if (
                self.locations is not None
                and location_name not in self.locations
            ):
                continue

            for gold_type in location.get("gold_type", []):
                product_name = gold_type.get("name")

                if not product_name:
                    continue

                if (
                    self.products is not None
                    and product_name not in self.products
                ):
                    continue

                for item in gold_type.get("data", []):
                    source_order += 1

                    records.append(
                        {
                            "query_date": str(query_date),
                            "location": location_name,
                            "product": product_name,
                            "buy": normalize_price(
                                item.get("gia_mua")
                            ),
                            "sell": normalize_price(
                                item.get("gia_ban")
                            ),
                            "updated_at": parse_updated_at(
                                item.get("updated_at")
                            ),
                            "crawl_time": crawl_time,
                            "_source_order": source_order,
                        }
                    )

        return records

    def _prepare_dataframe(self) -> pd.DataFrame:
        """Chuẩn hóa dữ liệu trước khi lưu."""

        if not self.rows:
            return pd.DataFrame()

        df = pd.DataFrame(self.rows)

        required_columns = [
            "query_date",
            "location",
            "product",
            "buy",
            "sell",
            "updated_at",
            "crawl_time",
        ]

        for column in required_columns:
            if column not in df.columns:
                df[column] = pd.NA

        if "_source_order" not in df.columns:
            df["_source_order"] = range(len(df))

        df["query_date"] = (
            df["query_date"]
            .astype(str)
            .str.replace(".0", "", regex=False)
        )

        df["buy"] = df["buy"].apply(normalize_price)
        df["sell"] = df["sell"].apply(normalize_price)
        df["updated_at"] = df["updated_at"].apply(parse_updated_at)
        df["crawl_time"] = pd.to_datetime(
            df["crawl_time"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "query_date",
                "location",
                "product",
                "updated_at",
            ]
        )

        sort_columns = [
            "query_date",
            "location",
            "product",
            "updated_at",
            "crawl_time",
            "_source_order",
        ]

        df = df.sort_values(sort_columns, kind="stable")

        if self.mode == "snapshot":
            df = df.drop_duplicates(
                subset=[
                    "query_date",
                    "location",
                    "product",
                ],
                keep="last",
            )
        else:
            df = df.drop_duplicates(
                subset=[
                    "query_date",
                    "location",
                    "product",
                    "buy",
                    "sell",
                    "updated_at",
                ],
                keep="last",
            )

        return (
            df.drop(columns=["_source_order"], errors="ignore")
            .reset_index(drop=True)
        )

    def save(self) -> None:
        """Lưu dữ liệu ra CSV hoặc Parquet."""

        df = self._prepare_dataframe()

        if df.empty:
            logging.warning("Không có dữ liệu để lưu.")
            return

        self.output.parent.mkdir(parents=True, exist_ok=True)

        if self.output.suffix.lower() == ".parquet":
            df.to_parquet(self.output, index=False)
        else:
            df.to_csv(
                self.output,
                index=False,
                encoding="utf-8-sig",
            )

        self.rows = df.to_dict("records")

        logging.info(
            "Đã lưu %d dòng vào %s.",
            len(df),
            self.output,
        )

    def crawl(
        self,
        dates: Iterable[str],
        force: bool = False,
    ) -> None:
        """Crawl lần lượt các ngày và lưu incremental."""

        try:
            for query_date in tqdm(list(dates), desc="Downloading"):
                if (
                    not force
                    and query_date in self.completed_dates
                ):
                    continue

                payload = self.fetch(query_date)

                if payload is None:
                    continue

                parsed_rows = self.parse(query_date, payload)

                if not parsed_rows:
                    logging.warning(
                        "Không có dữ liệu phù hợp cho ngày %s.",
                        query_date,
                    )
                else:
                    self.rows.extend(parsed_rows)

                self.completed_dates.add(query_date)
                self.save()

                time.sleep(
                    random.uniform(
                        self.min_delay,
                        self.max_delay,
                    )
                )

        finally:
            self.session.close()


def show_mapping(title: str, mapping: Dict[str, str]) -> None:
    """Hiển thị danh sách keyword CLI."""

    print("\n%s\n" % title)

    for key, value in mapping.items():
        print("%-12s -> %s" % (key, value))


def build_parser() -> argparse.ArgumentParser:
    """Tạo CLI parser."""

    parser = argparse.ArgumentParser(
        description="Download and parse PNJ historical gold prices."
    )

    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=None,
        help="Số ngày lùi từ hôm nay. Mặc định: 180.",
    )
    parser.add_argument(
        "--start-date",
        help="Ngày bắt đầu theo định dạng YYYY-MM-DD.",
    )
    parser.add_argument(
        "--end-date",
        help="Ngày kết thúc theo định dạng YYYY-MM-DD.",
    )
    parser.add_argument(
        "-g",
        "--gold-type",
        help="Keyword sản phẩm, phân cách bằng dấu phẩy.",
    )
    parser.add_argument(
        "-l",
        "--location",
        help="Keyword khu vực, phân cách bằng dấu phẩy.",
    )
    parser.add_argument(
        "--mode",
        choices=["history", "snapshot"],
        default="snapshot",
        help=(
            "history: lưu toàn bộ dữ liệu; "
            "snapshot: chỉ lưu giá cuối ngày."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default="pnj_gold_snapshot.csv",
        help="Đường dẫn file CSV hoặc Parquet.",
    )
    parser.add_argument("--delay-min", type=float, default=1.0)
    parser.add_argument("--delay-max", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Crawl lại cả các ngày đã có trong file output.",
    )
    parser.add_argument("--list-products", action="store_true")
    parser.add_argument("--list-locations", action="store_true")

    return parser


def main() -> None:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args()

    if args.list_products:
        show_mapping("Available products:", PRODUCTS)
        return

    if args.list_locations:
        show_mapping("Available locations:", LOCATIONS)
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    selected_products = parse_keywords(
        args.gold_type,
        PRODUCTS,
        "gold-type",
    )
    selected_locations = parse_keywords(
        args.location,
        LOCATIONS,
        "location",
    )

    dates = generate_dates(
        start_date=args.start_date,
        end_date=args.end_date,
        days=args.days,
    )

    logging.info("Chuẩn bị crawl %d ngày.", len(dates))

    crawler = PNJGoldCrawler(
        output=args.output,
        mode=args.mode,
        products=selected_products,
        locations=selected_locations,
        min_delay=args.delay_min,
        max_delay=args.delay_max,
        retries=args.retries,
        timeout=args.timeout,
    )

    crawler.crawl(
        dates=dates,
        force=args.force,
    )


if __name__ == "__main__":
    main()
