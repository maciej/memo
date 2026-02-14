import os
import time
import click

from memo_helpers.cache import cache_get, cache_set
from memo_helpers.get_memo import get_note_titles
from memo_helpers.list_folder import notes_folder_names


def _maybe_timing(label: str, start: float) -> None:
    if os.getenv("MEMO_TIMING") != "1":
        return
    ms = (time.perf_counter() - start) * 1000.0
    click.echo(f"[timing] {label}: {ms:.1f}ms", err=True)


def _backend() -> str:
    """
    Select Notes listing backend.

    - auto (default): try sqlite, then fall back to AppleScript
    - sqlite: force sqlite (error if unavailable)
    - applescript: force AppleScript (even if sqlite works)
    """
    v = (os.getenv("MEMO_NOTES_BACKEND", "auto") or "").strip().lower()
    if v in ("", "auto"):
        return "auto"
    if v in ("sqlite", "sql", "db"):
        return "sqlite"
    if v in ("applescript", "osascript", "as"):
        return "applescript"
    return "auto"


def list_note_titles(folder: str = "") -> list[str]:
    """
    Prefer fast local SQLite listing when available; fall back to AppleScript.
    """
    backend = _backend()
    cache_key = f"note_titles:v1:{backend}:{folder}"
    cached = cache_get(cache_key)
    if isinstance(cached, list) and all(isinstance(x, str) for x in cached):
        if os.getenv("MEMO_TIMING") == "1":
            click.echo("[timing] notes_provider/cache_hit", err=True)
        return cached

    t0 = time.perf_counter()
    if backend == "applescript":
        out = get_note_titles(folder=folder)
        _maybe_timing("notes_provider/applescript_forced", t0)
        cache_set(cache_key, out)
        return out

    if backend == "sqlite":
        try:
            from memo_helpers.notes_sqlite import list_note_titles as sqlite_list
        except Exception as e:
            raise click.ClickException(
                f"SQLite Notes backend unavailable: {type(e).__name__}"
            )
        try:
            out = sqlite_list(folder=folder)
        except Exception as e:
            raise click.ClickException(
                f"SQLite Notes backend failed: {type(e).__name__}"
            )
        _maybe_timing("notes_provider/sqlite_forced", t0)
        cache_set(cache_key, out)
        return out

    # auto
    try:
        from memo_helpers.notes_sqlite import list_note_titles as sqlite_list

        out = sqlite_list(folder=folder)
        _maybe_timing("notes_provider/sqlite_ok", t0)
        cache_set(cache_key, out)
        return out
    except Exception as e:
        if os.getenv("MEMO_TIMING") == "1":
            click.echo(
                f"[timing] notes_provider/sqlite_fallback: {type(e).__name__}", err=True
            )

    out = get_note_titles(folder=folder)
    _maybe_timing("notes_provider/applescript", t0)
    cache_set(cache_key, out)
    return out


def list_folder_names() -> list[str]:
    backend = _backend()
    cache_key = f"folder_names:v1:{backend}"
    cached = cache_get(cache_key)
    if isinstance(cached, list) and all(isinstance(x, str) for x in cached):
        if os.getenv("MEMO_TIMING") == "1":
            click.echo("[timing] notes_provider/cache_hit_folders", err=True)
        return cached

    t0 = time.perf_counter()
    if backend == "applescript":
        out = notes_folder_names()
        _maybe_timing("notes_provider/applescript_folders_forced", t0)
        cache_set(cache_key, out)
        return out

    if backend == "sqlite":
        try:
            from memo_helpers.notes_sqlite import list_folder_names as sqlite_folders
        except Exception as e:
            raise click.ClickException(
                f"SQLite Notes backend unavailable: {type(e).__name__}"
            )
        try:
            out = sqlite_folders()
        except Exception as e:
            raise click.ClickException(
                f"SQLite Notes backend failed: {type(e).__name__}"
            )
        _maybe_timing("notes_provider/sqlite_folders_forced", t0)
        cache_set(cache_key, out)
        return out

    # auto
    try:
        from memo_helpers.notes_sqlite import list_folder_names as sqlite_folders

        out = sqlite_folders()
        _maybe_timing("notes_provider/sqlite_folders_ok", t0)
        cache_set(cache_key, out)
        return out
    except Exception as e:
        if os.getenv("MEMO_TIMING") == "1":
            click.echo(
                f"[timing] notes_provider/sqlite_folders_fallback: {type(e).__name__}",
                err=True,
            )

    out = notes_folder_names()
    _maybe_timing("notes_provider/applescript_folders", t0)
    cache_set(cache_key, out)
    return out
