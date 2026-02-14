import subprocess
import click

FOLDER_SEPARATOR = "|||"


def _build_tree(folders_with_parents):
    """Build a folder tree from a flat list of (name, parent) tuples."""
    children = {}
    for name, parent in folders_with_parents:
        children.setdefault(parent, []).append(name)
    return children


def _render_tree(children, parent="", indent=0):
    """Render the folder tree as indented text."""
    lines = []
    for name in children.get(parent, []):
        lines.append(" " * indent + name)
        if name in children:
            lines.extend(_render_tree(children, name, indent + 2))
    return lines


def notes_folder_names():
    """Return a flat list of Notes folder names (no tree rendering)."""
    script = """
    set prevTIDs to AppleScript's text item delimiters
    set AppleScript's text item delimiters to linefeed
    set outLines to {}

    tell application "Notes"
        repeat with f in every folder
            set end of outLines to (name of f as string)
        end repeat
    end tell

    set output to outLines as text
    set AppleScript's text item delimiters to prevTIDs
    return output
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )
        raw = result.stdout.strip()
        if not raw:
            return []
        return [line.strip() for line in raw.split("\n") if line.strip()]
    except subprocess.CalledProcessError as e:
        stderr = ""
        try:
            stderr = (e.stderr or "").strip()
        except Exception:
            stderr = ""
        if stderr:
            raise click.ClickException(f"AppleScript execution failed.\n\n{stderr}")
        raise click.ClickException(f"AppleScript execution failed: {e}")


def notes_folders():
    script = f"""
    set prevTIDs to AppleScript's text item delimiters
    set AppleScript's text item delimiters to linefeed
    set outLines to {{}}

    tell application "Notes"
        repeat with f in every folder
            set fName to name of f as string
            try
                set c to container of f
                set cClass to class of c as text
                if cClass is "folder" then
                    set parentName to name of c as string
                else
                    set parentName to ""
                end if
            on error
                set parentName to ""
            end try
            set end of outLines to (fName & "{FOLDER_SEPARATOR}" & parentName)
        end repeat
    end tell

    set output to outLines as text
    set AppleScript's text item delimiters to prevTIDs
    return output
    """

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )
        raw = result.stdout.strip()
        if not raw:
            return ""

        folders_with_parents = []
        for line in raw.split("\n"):
            if FOLDER_SEPARATOR in line:
                name, parent = line.split(FOLDER_SEPARATOR, 1)
                folders_with_parents.append((name.strip(), parent.strip()))

        children = _build_tree(folders_with_parents)
        lines = _render_tree(children)
        return "\n".join(lines)
    except subprocess.CalledProcessError as e:
        stderr = ""
        try:
            stderr = (e.stderr or "").strip()
        except Exception:
            stderr = ""
        if stderr:
            raise click.ClickException(f"AppleScript execution failed.\n\n{stderr}")
        raise click.ClickException(f"AppleScript execution failed: {e}")
        return ""
