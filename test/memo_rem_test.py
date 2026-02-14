from click.testing import CliRunner
from memo.memo import cli


def _patch_reminders(monkeypatch):
    import memo.memo as memo_mod
    import click
    import datetime

    # Map/list shape matches get_reminder() contract in memo_helpers/get_memo.py
    reminder_map = {
        1: ("rem-id-1", "Test reminder", datetime.datetime(2026, 1, 1, 12, 0, 0)),
    }
    reminder_list = ["Test reminder | 2026-01-01 12:00:00"]
    monkeypatch.setattr(memo_mod, "get_reminder", lambda: [reminder_map, reminder_list])

    monkeypatch.setattr(
        memo_mod,
        "complete_reminder",
        lambda _rid: click.secho("\nReminder marked successfully as completed.", fg="green"),
    )
    monkeypatch.setattr(
        memo_mod,
        "delete_reminder",
        lambda _rid: click.secho("\nReminder deleted successfully.", fg="green"),
    )


def test_rem(monkeypatch):
    _patch_reminders(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["rem"])
    assert result.exit_code == 0
    assert "Your Reminders:" in result.output


def test_rem_complete(monkeypatch):
    _patch_reminders(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["rem", "--complete"], input="1")
    assert result.exit_code == 0
    assert "Reminder marked successfully as completed." in result.output


def test_rem_delete(monkeypatch):
    _patch_reminders(monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, ["rem", "--delete"], input="1")
    assert result.exit_code == 0
    assert "Reminder deleted successfully." in result.output
