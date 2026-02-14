import os
import sqlite3
import time
import click


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
        q = """
        select
            n.ZTITLE1 as title,
            f.ZTITLE2 as folder
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
        title = r["title"] or ""
        title = title.strip() if isinstance(title, str) else ""
        if not title:
            title = "(Untitled)"

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
        if not name or name in _DELETED_TRANSLATIONS:
            continue
        out.append(name)
    out.sort(key=str.casefold)
    return out

