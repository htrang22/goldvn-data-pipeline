"""Ghi lại manifest cho mỗi lần chạy pipeline: hash + timestamp của input/output."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_run_manifest(
    raw_files: dict,
    final_files: dict,
    start_date: str,
    end_date: str,
    manifest_path: Path,
) -> None:
    manifest = {
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "raw_inputs": {},
        "final_outputs": {},
    }

    for name, path in raw_files.items():
        path = Path(path)
        if path.exists():
            manifest["raw_inputs"][name] = {
                "path": str(path),
                "sha256": _sha256_of_file(path),
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        else:
            manifest["raw_inputs"][name] = {"path": str(path), "error": "file not found"}

    for name, path in final_files.items():
        path = Path(path)
        if path.exists():
            manifest["final_outputs"][name] = {
                "path": str(path),
                "sha256": _sha256_of_file(path),
            }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)