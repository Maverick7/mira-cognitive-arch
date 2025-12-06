# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import Dict
from ..config import DATA_DIR

def _is_within_base(path: Path, base: Path) -> bool:
    try:
        return base.resolve() in path.resolve().parents or path.resolve() == base.resolve()
    except Exception:
        return False

def read_file(rel_path: str, base_dir: Path | None = None, max_bytes: int = 8192) -> Dict[str, object]:
    base = base_dir or DATA_DIR
    try:
        p = (base / rel_path).resolve()
        if not _is_within_base(p, base):
            return {"ok": False, "error": "Path outside sandbox"}
        if not p.exists() or not p.is_file():
            return {"ok": False, "error": "File not found"}
        data = p.read_bytes()[:max_bytes]
        try:
            content = data.decode("utf-8", errors="replace")
        except Exception:
            content = ""
        return {"ok": True, "content": content, "truncated": p.stat().st_size > len(data)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

