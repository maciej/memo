import os
import sqlite3
import time
import click
from dataclasses import dataclass


_DELETED_TRANSLATIONS = {
    "Recently Deleted",
    "Nylig slettet",
    "Senast raderade",
    "Senest slettet",
    "Zuletzt gelöscht",
    "Supprimés récemment",
    "Eliminados recientemente",
    "Eliminati di recente",
    "Recent verwijderd",
    "Ostatnio usunięte",
    "Недавно удалённые",
    "Apagados recentemente",
    "Apagadas recentemente",
    "最近删除",
    "最近刪除",
    "最近削除した項目",
    "최근 삭제된 항목",
    "Son Silinenler",
    "Äskettäin poistetut",
    "Nedávno smazané",
    "Πρόσφατα διαγραμμένα",
    "Nemrég töröltek",
    "Șterse recent",
    "Nedávno vymazané",
    "เพิ่งลบ",
    "Đã xóa gần đây",
    "Нещодавно видалені",
}

@dataclass(frozen=True, slots=True)
class NoteMeta:
    folder: str
    title: str
    # Best-effort stable identifier from the DB. Not guaranteed to exist across schema variants.
    identifier: str | None = None
    # Raw Notes title used for best-effort AppleScript lookups when available.
    # This may be empty even when `title` is a snippet-derived display title.
    lookup_title: str | None = None
    # Primary key from ZICCLOUDSYNCINGOBJECT for stable display/cache keys.
    pk: int | None = None


def _maybe_timing(label: str, start: float) -> None:
    if os.getenv("MEMO_TIMING") != "1":
        return
    ms = (time.perf_counter() - start) * 1000.0
    click.echo(f"[timing] {label}: {ms:.1f}ms", err=True)


def _default_db_path() -> str:
    # Note: this is private implementation detail of Apple Notes and may change.
    return os.path.expanduser("~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite")


def _connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.1)
    con.row_factory = sqlite3.Row
    return con


def _note_columns(con: sqlite3.Connection) -> set[str]:
    cols: set[str] = set()
    try:
        rows = con.execute("PRAGMA table_info(ZICCLOUDSYNCINGOBJECT)").fetchall()
    except Exception:
        return cols
    for r in rows:
        name = r["name"] if isinstance(r, sqlite3.Row) else None
        if isinstance(name, str):
            cols.add(name)
    return cols


def _best_title(
    *,
    raw_title: str,
    snippet: str | None,
    summary: str | None,
    pk: int | None,
) -> str:
    title = (raw_title or "").strip()
    if not title and snippet:
        title = " ".join(str(snippet).splitlines()).strip()
    if not title and summary:
        title = " ".join(str(summary).splitlines()).strip()
    if not title and pk is not None:
        return f"(Untitled #{pk})"
    return title or "(Untitled)"


def list_note_titles(folder: str = "") -> list[str]:
    """
    Fast path for `memo notes` listing (titles only).
    Returns ["Folder - Title", ...] or ["Title", ...] when folder is empty.
    """
    db_path = os.getenv("MEMO_NOTES_DB_PATH", _default_db_path())
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    folder_filter = (folder or "").strip()

    t0 = time.perf_counter()
    con = _connect(db_path)
    try:
        # Entities:
        # - ICNote: Z_ENT=12, title in ZTITLE1, folder FK in ZFOLDER
        # - ICFolder: Z_ENT=15, name in ZTITLE2, parent in ZPARENT
        cols = _note_columns(con)
        select_cols = [
            "n.Z_PK as pk",
            "n.ZTITLE1 as title",
        ]
        if "ZSNIPPET" in cols:
            select_cols.append("n.ZSNIPPET as snippet")
        if "ZSUMMARY" in cols:
            select_cols.append("n.ZSUMMARY as summary")
        select_cols.append("f.ZTITLE2 as folder")

        q = f"""
        select
            {", ".join(select_cols)}
        from ZICCLOUDSYNCINGOBJECT n
        left join ZICCLOUDSYNCINGOBJECT f
            on f.Z_PK = n.ZFOLDER and f.Z_ENT = 15
        where n.Z_ENT = 12
          and (n.ZMARKEDFORDELETION is null or n.ZMARKEDFORDELETION = 0)
          and (n.ZISPASSWORDPROTECTED is null or n.ZISPASSWORDPROTECTED = 0)
        """
        rows = con.execute(q).fetchall()
    finally:
        con.close()
    _maybe_timing("notes_sqlite/list_note_titles/query", t0)

    t_parse = time.perf_counter()
    out: list[str] = []
    for r in rows:
        pk = r["pk"] if isinstance(r, sqlite3.Row) and "pk" in r.keys() else None
        pk = int(pk) if isinstance(pk, int) else None
        raw_title = r["title"] if isinstance(r, sqlite3.Row) else ""
        snippet = r["snippet"] if isinstance(r, sqlite3.Row) and "snippet" in r.keys() else None
        summary = r["summary"] if isinstance(r, sqlite3.Row) and "summary" in r.keys() else None
        title = _best_title(
            raw_title=str(raw_title or ""),
            snippet=snippet if isinstance(snippet, str) else None,
            summary=summary if isinstance(summary, str) else None,
            pk=pk,
        )

        folder_name = r["folder"] or ""
        folder_name = folder_name.strip() if isinstance(folder_name, str) else ""
        if folder_name in _DELETED_TRANSLATIONS:
            continue

        if folder_filter:
            # Keep current UX: folder filter is a substring match.
            if folder_name and folder_filter not in folder_name:
                continue

        if folder_name:
            out.append(f"{folder_name} - {title}")
        else:
            out.append(title)
    out.sort(key=str.casefold)
    _maybe_timing("notes_sqlite/list_note_titles/format", t_parse)
    return out


def list_folder_names() -> list[str]:
    db_path = os.getenv("MEMO_NOTES_DB_PATH", _default_db_path())
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    t0 = time.perf_counter()
    con = _connect(db_path)
    try:
        rows = con.execute(
            """
            select distinct ZTITLE2 as folder
            from ZICCLOUDSYNCINGOBJECT
            where Z_ENT = 15 and ZTITLE2 is not null and ZTITLE2 != ''
            """
        ).fetchall()
    finally:
        con.close()
    _maybe_timing("notes_sqlite/list_folder_names/query", t0)

    out = []
    for r in rows:
        name = (r["folder"] or "").strip()
        if not name:
            continue
        out.append(name)
    out.sort(key=str.casefold)
    return out


def list_folders_with_parents() -> list[tuple[str, str]]:
    """
    Return a list of (folder_name, parent_folder_name) pairs from NoteStore.sqlite.

    Entities:
    - ICFolder: Z_ENT=15, name in ZTITLE2, parent FK in ZPARENT
    """
    db_path = os.getenv("MEMO_NOTES_DB_PATH", _default_db_path())
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    t0 = time.perf_counter()
    con = _connect(db_path)
    try:
        cols = _note_columns(con)
        title_col = "ZTITLE2" if "ZTITLE2" in cols else "ZTITLE1"
        parent_fk = None
        for c in ("ZPARENT", "ZPARENT1", "ZPARENT2"):
            if c in cols:
                parent_fk = c
                break

        if parent_fk:
            q = f"""
            select
                f.{title_col} as name,
                p.{title_col} as parent
            from ZICCLOUDSYNCINGOBJECT f
            left join ZICCLOUDSYNCINGOBJECT p
                on p.Z_PK = f.{parent_fk} and p.Z_ENT = 15
            where f.Z_ENT = 15 and f.{title_col} is not null and f.{title_col} != ''
            """
        else:
            # Schema variant without a visible parent FK; still return a flat listing.
            q = f"""
            select
                f.{title_col} as name,
                '' as parent
            from ZICCLOUDSYNCINGOBJECT f
            where f.Z_ENT = 15 and f.{title_col} is not null and f.{title_col} != ''
            """
        rows = con.execute(q).fetchall()
    finally:
        con.close()
    _maybe_timing("notes_sqlite/list_folders_with_parents/query", t0)

    out: list[tuple[str, str]] = []
    for r in rows:
        name = (r["name"] or "").strip()
        if not name:
            continue
        parent = (r["parent"] or "").strip()
        out.append((name, parent))
    return out


def list_notes_meta(folder: str = "") -> list[NoteMeta]:
    """
    Best-effort structured listing for `memo notes --search`.

    Returns NoteMeta(folder, title, identifier?) for all notes that are:
    - not marked for deletion
    - not password protected
    - not in Recently Deleted (translated)

    Folder filtering keeps the existing UX: substring match on folder name.
    """
    db_path = os.getenv("MEMO_NOTES_DB_PATH", _default_db_path())
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    folder_filter = (folder or "").strip()

    con = _connect(db_path)
    try:
        cols = _note_columns(con)
        t0 = time.perf_counter()
        select_cols = [
            "n.Z_PK as pk",
            "n.ZTITLE1 as title",
        ]
        if "ZSNIPPET" in cols:
            select_cols.append("n.ZSNIPPET as snippet")
        if "ZSUMMARY" in cols:
            select_cols.append("n.ZSUMMARY as summary")
        if "ZIDENTIFIER" in cols:
            select_cols.append("n.ZIDENTIFIER as identifier")
        select_cols.append("f.ZTITLE2 as folder")

        q = f"""
        select
            {", ".join(select_cols)}
        from ZICCLOUDSYNCINGOBJECT n
        left join ZICCLOUDSYNCINGOBJECT f
            on f.Z_PK = n.ZFOLDER and f.Z_ENT = 15
        where n.Z_ENT = 12
          and (n.ZMARKEDFORDELETION is null or n.ZMARKEDFORDELETION = 0)
          and (n.ZISPASSWORDPROTECTED is null or n.ZISPASSWORDPROTECTED = 0)
        """
        rows = con.execute(q).fetchall()
        _maybe_timing("notes_sqlite/list_notes_meta/query", t0)
    finally:
        con.close()

    t_parse = time.perf_counter()
    out: list[NoteMeta] = []
    for r in rows:
        pk = r["pk"] if isinstance(r, sqlite3.Row) and "pk" in r.keys() else None
        pk = int(pk) if isinstance(pk, int) else None

        raw_title = r["title"] if isinstance(r, sqlite3.Row) else ""
        raw_title = raw_title.strip() if isinstance(raw_title, str) else ""
        snippet = r["snippet"] if isinstance(r, sqlite3.Row) and "snippet" in r.keys() else None
        summary = r["summary"] if isinstance(r, sqlite3.Row) and "summary" in r.keys() else None
        title = _best_title(
            raw_title=str(raw_title or ""),
            snippet=snippet if isinstance(snippet, str) else None,
            summary=summary if isinstance(summary, str) else None,
            pk=pk,
        )

        folder_name = r["folder"] if isinstance(r, sqlite3.Row) else None
        folder_name = folder_name or ""
        folder_name = folder_name.strip() if isinstance(folder_name, str) else ""
        if folder_name in _DELETED_TRANSLATIONS:
            continue

        if folder_filter:
            if folder_name and folder_filter not in folder_name:
                continue

        identifier = None
        if isinstance(r, sqlite3.Row) and "identifier" in r.keys():
            raw = r["identifier"]
            if isinstance(raw, str) and raw.strip():
                identifier = raw.strip()

        out.append(
            NoteMeta(
                folder=folder_name,
                title=title,
                identifier=identifier,
                lookup_title=raw_title,
                pk=pk,
            )
        )

    out.sort(key=lambda x: f"{x.folder}\n{x.title}".casefold())
    _maybe_timing("notes_sqlite/list_notes_meta/format", t_parse)
    return out
