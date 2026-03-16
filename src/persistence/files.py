from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileStorage:
    def __init__(self, base_dir: str = "data") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _safe_filename(self, name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "", name)

    def save_json(self, directory: str, filename: str, data: dict[str, Any]) -> Path:
        dir_path = self._base / directory
        dir_path.mkdir(parents=True, exist_ok=True)

        safe_name = self._safe_filename(filename)
        file_path = dir_path / f"{safe_name}.json"
        temp_path = dir_path / f".tmp_{safe_name}.json"

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        temp_path.replace(file_path)
        logger.debug("Saved JSON: %s", file_path)
        return file_path

    def load_json(self, directory: str, filename: str) -> dict[str, Any] | None:
        safe_name = self._safe_filename(filename)
        file_path = self._base / directory / f"{safe_name}.json"

        if not file_path.exists():
            return None

        with open(file_path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def list_json(self, directory: str) -> list[str]:
        dir_path = self._base / directory
        if not dir_path.exists():
            return []
        return [p.stem for p in sorted(dir_path.glob("*.json"))]

    def delete_json(self, directory: str, filename: str) -> bool:
        safe_name = self._safe_filename(filename)
        file_path = self._base / directory / f"{safe_name}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def append_jsonl(
        self, directory: str, filename: str, entry: dict[str, Any]
    ) -> Path:
        dir_path = self._base / directory
        dir_path.mkdir(parents=True, exist_ok=True)

        safe_name = self._safe_filename(filename)
        file_path = dir_path / f"{safe_name}.jsonl"

        with open(file_path, "a", encoding="utf-8") as f:
            line = json.dumps(entry, ensure_ascii=False, default=str)
            f.write(line + "\n")

        return file_path

    def read_jsonl(self, directory: str, filename: str) -> list[dict[str, Any]]:
        safe_name = self._safe_filename(filename)
        file_path = self._base / directory / f"{safe_name}.jsonl"

        if not file_path.exists():
            return []

        entries: list[dict[str, Any]] = []
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def create_backup(self, source_dir: str, backup_name: str | None = None) -> Path:
        source = self._base / source_dir
        if not source.exists():
            raise FileNotFoundError(f"Source directory not found: {source}")

        if backup_name is None:
            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{source_dir}_{ts}"

        backup_path = self._base / "backups" / backup_name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, backup_path)
        logger.info("Created backup: %s", backup_path)
        return backup_path

    def load_lore_directory(self, lore_dir: str) -> dict[str, list[dict[str, Any]]]:
        lore_path = Path(lore_dir)
        if not lore_path.exists():
            logger.warning("Lore directory not found: %s", lore_dir)
            return {}

        result: dict[str, list[dict[str, Any]]] = {}
        for category_dir in lore_path.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                entries: list[dict[str, Any]] = []
                for json_file in sorted(category_dir.glob("*.json")):
                    with open(json_file, encoding="utf-8") as f:
                        entries.append(json.load(f))
                result[category] = entries

        return result
