from click.testing import CliRunner
from memo.memo import cli


def _patch_notes(monkeypatch):
    # Patch imported symbols in memo.memo (not memo_helpers.*) because memo.memo uses `from ... import ...`.
    import memo.memo as memo_mod
    import click

    monkeypatch.setattr(
        memo_mod,
        "list_note_titles",
        lambda folder="": ["Work - Alpha", "Work - Beta"] if not folder else ["Work - Alpha"],
    )
    monkeypatch.setattr(memo_mod, "list_folder_names", lambda: ["Work", "Personal"])
    monkeypatch.setattr(memo_mod, "list_folders_tree", lambda: "Personal\nWork\n  Sub")

    # Provide stable IDs so edit/move/delete code paths can select something.
    note_map = {1: ("note-id-1", "Work - Alpha"), 2: ("note-id-2", "Work - Beta")}
    notes_list = ["Work - Alpha", "Work - Beta"]
    monkeypatch.setattr(memo_mod, "get_note", lambda folder="": [note_map, notes_list])

    monkeypatch.setattr(memo_mod, "edit_note", lambda note_id: None)

    def _delete_note(_note_id):
        click.secho("\nNote deleted successfully.", fg="green")

    monkeypatch.setattr(memo_mod, "delete_note", _delete_note)


def test_notes(monkeypatch):
    # Listing should not depend on local Notes state.
    # (The real implementation may use sqlite or AppleScript, depending on environment.)
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes"])
    assert result.exit_code == 0
    assert "All your notes:" in result.output


def test_notes_folder_without_folder_name():
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--folder"])
    assert result.exit_code == 2
    assert "Error: Option '--folder' requires an argument." in result.output


def test_notes_folder_not_exists(monkeypatch):
    # Folder validation uses memo's backend; patch to deterministic list.
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--folder", "ksndclskdnc"])
    assert result.exit_code == 0
    assert "The folder does not exists." in result.output


def test_notes_add_no_folder():
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--add"])
    assert result.exit_code == 2
    assert (
        "Error: --add must be used indicating a folder to create the note to."
        in result.output
    )


def test_notes_edit(monkeypatch):
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--edit"], input="1")
    assert result.exit_code == 0
    assert "Enter the number of the note you want to edit:" in result.output


def test_notes_edit_indexerror(monkeypatch):
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--edit"], input="9999")
    assert result.exit_code == 1


def test_notes_delete(monkeypatch):
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--delete"], input="1")
    assert result.exit_code == 0
    assert "Note deleted successfully." in result.output


def test_notes_delete_indexerror(monkeypatch):
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--delete"], input="9999")
    assert result.exit_code == 1


def test_notes_move_indexerror(monkeypatch):
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--move"], input="9999")
    assert result.exit_code == 1


def test_notes_flist(monkeypatch):
    _patch_notes(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["notes", "--flist"])
    assert result.exit_code == 0
    assert "Folders and subfolders in Notes:" in result.output
