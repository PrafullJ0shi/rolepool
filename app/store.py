"""JSON read/write helpers with stable formatting so git diffs stay readable."""
from __future__ import annotations

import json
from pathlib import Path


def load(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return default


def save(path: Path, obj, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        txt = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False)
    path.write_text(txt + "\n")
