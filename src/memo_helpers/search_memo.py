import json
import os
import shlex
import subprocess
import sys
import tempfile

from memo_helpers.notes_provider import list_notes_meta


def fuzzy_notes(folder: str = "") -> None:
    """
    Interactive fuzzy finder for notes.

    Implementation notes:
    - Listing uses memo's Notes provider (sqlite when available, else AppleScript).
    - Preview is lazy: body is fetched on-demand via AppleScript and cached on disk.
    """
    notes = list_notes_meta(folder=folder)

    with tempfile.TemporaryDirectory() as tmpdirname:
        map_path = os.path.join(tmpdirname, "notes_map_v1.json")

        items: dict[str, dict] = {}
        lines: list[str] = []
        for i, n in enumerate(notes, start=1):
            key = str(i)
            folder_name = str(n.get("folder") or "")
            title = str(n.get("title") or "")
            display = f"{folder_name} - {title}" if folder_name else title
            cache_key = (
                n.get("note_id")
                or n.get("identifier")
                or (str(n.get("pk")) if n.get("pk") is not None else None)
                or key
            )
            items[key] = {
                "folder": folder_name,
                "title": title,
                "identifier": n.get("identifier"),
                "note_id": n.get("note_id"),
                "lookup_title": n.get("lookup_title"),
                "pk": n.get("pk"),
                "cache_key": cache_key,
            }
            lines.append(f"{key}\t{display}")

        with open(map_path, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, ensure_ascii=True)

        map_q = shlex.quote(map_path)
        py = shlex.quote(sys.executable or "python3")
        # Use numeric key (field 1) for preview, to avoid shell-escaping note titles.
        #
        # fzf runs `--preview` and some `--bind` actions through $SHELL -c.
        # When users run fish, fish-specific parsing breaks POSIX-y snippets.
        # Force a predictable shell for fzf to avoid preview breakage.
        env = os.environ.copy()
        env["SHELL"] = os.getenv("MEMO_FZF_SHELL", "/bin/sh")
        fzf_command = f"""
        fzf --style=full \\
            --border --padding=1,2 \\
            --border-label=' Your Notes ' --input-label=' Input ' --header-label=' Note ' \\
            --delimiter='\\t' --with-nth=2.. \\
            --preview='{py} -m memo_helpers.fzf_preview_notes --map {map_q} --key {{1}} | if command -v bat >/dev/null 2>&1; then bat --style=plain --color=always --language=markdown -; else cat; fi' \\
            --preview-window=right:60%:wrap:cycle \\
            --bind='ctrl-d:preview-down,ctrl-u:preview-up' \\
            --bind='result:transform-list-label:
                if [ -z \"$FZF_QUERY\" ]; then
                echo \" $FZF_MATCH_COUNT items \"
                else
                echo \" $FZF_MATCH_COUNT matches for [$FZF_QUERY] \"
                fi' \\
            --bind='focus:transform-preview-label:if [ -n \"{{1}}\" ]; then printf \" Previewing [%s] \" \"{{1}}\"; fi' \\
            --color='border:#aaaaaa,label:#cccccc' \\
            --color='preview-border:#9999cc,preview-label:#ccccff' \\
            --color='list-border:#669966,list-label:#99cc99' \\
            --color='input-border:#996666,input-label:#ffcccc' \\
            --color='header-border:#6699cc,header-label:#99ccff'
        """
        subprocess.run(
            fzf_command,
            shell=True,
            cwd=tmpdirname,
            env=env,
            input="\n".join(lines) + ("\n" if lines else ""),
            text=True,
        )
