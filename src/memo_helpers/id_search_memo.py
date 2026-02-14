import subprocess


def _escape_applescript_string(s: str) -> str:
    # AppleScript string literal escaping for inclusion inside double quotes.
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def id_search_memo(note_id: str) -> subprocess.CompletedProcess:
    script = f"""
        tell application "Notes"
            set selectedNote to first note whose id is "{note_id}"
            return body of selectedNote
        end tell
        """
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result


def note_body_by_folder_title(folder: str, title: str) -> subprocess.CompletedProcess:
    folder_escaped = _escape_applescript_string(folder)
    title_escaped = _escape_applescript_string(title)
    if folder_escaped:
        script = f"""
            tell application "Notes"
                set theFolder to first folder whose name is "{folder_escaped}"
                set selectedNote to first note of theFolder whose name is "{title_escaped}"
                return body of selectedNote
            end tell
        """
    else:
        script = f"""
            tell application "Notes"
                set selectedNote to first note whose name is "{title_escaped}"
                return body of selectedNote
            end tell
        """
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
