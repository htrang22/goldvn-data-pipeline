"""Điểm chạy chính của pipeline dữ liệu GoldVN."""

from config import ensure_data_directories


def main() -> None:
    """Khởi tạo thư mục; các bước xử lý sẽ được tách từ notebook nguồn."""

    ensure_data_directories()
    print("Đã khởi tạo cấu trúc dữ liệu GoldVN.")
    print("Bước tiếp theo: triển khai các module tải, làm sạch và tính return.")


if __name__ == "__main__":
    main()

