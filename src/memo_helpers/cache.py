import json
import os
import time
from pathlib import Path


def _cache_dir() -> Path:
    # Prefer XDG; macOS users may not have it set, so fall back to ~/.cache.
    base = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    return Path(base) / "memo"


def _cache_path() -> Path:
    return _cache_dir() / "cache_v1.json"


def _ttl_seconds() -> int:
    raw = os.getenv("MEMO_CACHE_TTL_SECONDS", "30")
    try:
        return max(0, int(raw))
    except ValueError:
        return 30


def cache_get(key: str):
    if os.getenv("MEMO_NO_CACHE") == "1":
        return None
    ttl = _ttl_seconds()
    if ttl <= 0:
        return None

    p = _cache_path()
    if not p.exists():
        return None

    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

    entry = obj.get(key)
    if not isinstance(entry, dict):
        return None
    ts = entry.get("ts")
    if not isinstance(ts, (int, float)):
        return None
    if (time.time() - float(ts)) > ttl:
        return None
    return entry.get("data")


def cache_set(key: str, data):
    if os.getenv("MEMO_NO_CACHE") == "1":
        return
    ttl = _ttl_seconds()
    if ttl <= 0:
        return

    p = _cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    obj = {}
    try:
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(obj, dict):
                obj = {}
    except Exception:
        obj = {}

    obj[key] = {"ts": time.time(), "data": data}
    p.write_text(json.dumps(obj, ensure_ascii=True), encoding="utf-8")

