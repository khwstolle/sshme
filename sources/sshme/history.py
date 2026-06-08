"""
MRU connection history stored under XDG_DATA_HOME.
"""

import json
import os
import sys
from pathlib import Path

__all__ = ["load", "record", "HISTORY_MAX"]

HISTORY_MAX = 10

_HISTORY_PATH = (
    Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser() / "sshme" / "history.json"
)


def load() -> list[str]:
    try:
        data = json.loads(_HISTORY_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def record(host: str) -> None:
    history = [h for h in load() if h != host]
    history.insert(0, host)
    try:
        _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _HISTORY_PATH.write_text(json.dumps(history[:HISTORY_MAX]))
    except OSError as exc:
        print(f"sshme: warning: could not write history: {exc}", file=sys.stderr)
