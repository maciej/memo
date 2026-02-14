import argparse
import json
import os
from pathlib import Path

from memo_helpers.id_search_memo import id_search_memo, note_body_by_folder_title
from memo_helpers.md_converter import md_converter


def _load_map(path: Path) -> dict[str, dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, dict) and "items" in obj and isinstance(obj["items"], dict):
        return obj["items"]
    if isinstance(obj, dict) and all(isinstance(k, str) for k in obj.keys()):
        return obj  # legacy/loose
    raise ValueError("Invalid preview map JSON")


def _cache_path(map_path: Path, key: str) -> Path:
    # Keep cached previews next to the map file, inside a stable subdir.
    d = map_path.parent / "preview_cache_v1"
    d.mkdir(parents=True, exist_ok=True)
    safe_key = "".join(ch for ch in (key or "") if ch.isalnum() or ch in ("_", "-")) or "0"
    return d / f"{safe_key}.md"


def _render_markdown(item: dict) -> str:
    note_id = item.get("note_id")
    identifier = item.get("identifier")
    folder = item.get("folder") or ""
    title = item.get("title") or ""
    lookup_title = item.get("lookup_title")

    if isinstance(note_id, str) and note_id.strip():
        result = id_search_memo(note_id.strip())
    elif isinstance(identifier, str) and identifier.strip():
        # For sqlite listings, `identifier` is best-effort. If it doesn't match
        # AppleScript note ids on a given macOS version, we fall back.
        result = id_search_memo(identifier.strip())
    else:
        # If our display title is a placeholder, try looking up by empty name.
        # This is best-effort and can still be ambiguous when multiple untitled notes exist.
        effective_title = title
        if title == "(Untitled)" and isinstance(lookup_title, str):
            effective_title = lookup_title
        result = note_body_by_folder_title(str(folder), str(effective_title))

    if getattr(result, "returncode", 1) != 0:
        # If identifier-based lookup fails, try the folder/title fallback.
        if (
            not (isinstance(note_id, str) and note_id.strip())
            and isinstance(identifier, str)
            and identifier.strip()
        ):
            effective_title = title
            if title == "(Untitled)" and isinstance(lookup_title, str):
                effective_title = lookup_title
            result = note_body_by_folder_title(str(folder), str(effective_title))

    if getattr(result, "returncode", 1) != 0:
        err = (getattr(result, "stderr", "") or "").strip()
        return f"(preview error)\n\n{err}" if err else "(preview error)"

    md, _html = md_converter(result)
    return md


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m memo_helpers.fzf_preview_notes")
    p.add_argument("--map", required=True, help="Path to notes preview map JSON")
    p.add_argument("--key", required=True, help="Numeric key from fzf selection")
    args = p.parse_args(argv)

    map_path = Path(args.map)
    key = str(args.key)

    try:
        items = _load_map(map_path)
        item = items.get(key)
        if not isinstance(item, dict):
            print("(no preview)")
            return 0

        cache_key = item.get("cache_key")
        cache = _cache_path(map_path, str(cache_key) if cache_key else key)
        if cache.exists() and os.path.getsize(cache) > 0:
            print(cache.read_text(encoding="utf-8", errors="replace"))
            return 0

        md = _render_markdown(item)
        cache.write_text(md, encoding="utf-8")
        print(md)
        return 0
    except Exception as e:
        print(f"(preview error: {type(e).__name__})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
