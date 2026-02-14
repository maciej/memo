import os
import time
import click

from memo_helpers.cache import cache_get, cache_set
from memo_helpers.get_memo import get_note_titles
from memo_helpers.get_memo import get_note
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


def list_notes_meta(folder: str = "") -> list[dict]:
    """
    Structured listing used by `memo notes --search`.

    Returns list of dicts:
    {
        "folder": str,
        "title": str,
        "identifier": str|None,
        "note_id": str|None,
        "lookup_title": str|None,
        "pk": int|None,
    }
    - sqlite backend: best-effort returns identifier when available (note_id is None)
    - applescript backend: returns note_id (AppleScript id) and no identifier
    """
    backend = _backend()
    cache_key = f"notes_meta:v1:{backend}:{folder}"
    cached = cache_get(cache_key)
    if isinstance(cached, list) and all(isinstance(x, dict) for x in cached):
        if os.getenv("MEMO_TIMING") == "1":
            click.echo("[timing] notes_provider/cache_hit_meta", err=True)
        return cached

    t0 = time.perf_counter()
    if backend == "applescript":
        note_map, _ = get_note(folder=folder)
        out = []
        for _, (note_id, display) in note_map.items():
            # display is "Folder - Title" per AppleScript in get_note.
            folder_name = ""
            title = display
            if " - " in display:
                folder_name, title = display.split(" - ", 1)
            out.append(
                {
                    "folder": folder_name,
                    "title": title,
                    "identifier": None,
                    "note_id": note_id,
                    "lookup_title": title,
                    "pk": None,
                }
            )
        _maybe_timing("notes_provider/applescript_meta_forced", t0)
        cache_set(cache_key, out)
        return out

    if backend == "sqlite":
        try:
            from memo_helpers.notes_sqlite import list_notes_meta as sqlite_meta
        except Exception as e:
            raise click.ClickException(
                f"SQLite Notes backend unavailable: {type(e).__name__}"
            )
        try:
            notes = sqlite_meta(folder=folder)
        except Exception as e:
            raise click.ClickException(
                f"SQLite Notes backend failed: {type(e).__name__}"
            )
        out = [
            {
                "folder": n.folder,
                "title": n.title,
                "identifier": n.identifier,
                "note_id": None,
                "lookup_title": n.lookup_title,
                "pk": n.pk,
            }
            for n in notes
        ]
        _maybe_timing("notes_provider/sqlite_meta_forced", t0)
        cache_set(cache_key, out)
        return out

    # auto
    try:
        from memo_helpers.notes_sqlite import list_notes_meta as sqlite_meta

        notes = sqlite_meta(folder=folder)
        out = [
            {
                "folder": n.folder,
                "title": n.title,
                "identifier": n.identifier,
                "note_id": None,
                "lookup_title": n.lookup_title,
                "pk": n.pk,
            }
            for n in notes
        ]
        _maybe_timing("notes_provider/sqlite_meta_ok", t0)
        cache_set(cache_key, out)
        return out
    except Exception as e:
        if os.getenv("MEMO_TIMING") == "1":
            click.echo(
                f"[timing] notes_provider/sqlite_meta_fallback: {type(e).__name__}",
                err=True,
            )

    note_map, _ = get_note(folder=folder)
    out = []
    for _, (note_id, display) in note_map.items():
        folder_name = ""
        title = display
        if " - " in display:
            folder_name, title = display.split(" - ", 1)
        out.append(
            {
                "folder": folder_name,
                "title": title,
                "identifier": None,
                "note_id": note_id,
                "lookup_title": title,
                "pk": None,
            }
        )
    _maybe_timing("notes_provider/applescript_meta", t0)
    cache_set(cache_key, out)
    return out
