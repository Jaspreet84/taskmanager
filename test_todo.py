"""Comprehensive test suite for todo-cli. Powered by GEMINI."""
import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import gspread
import pytest
from click.testing import CliRunner

from cli import cli
from config import Config
from models import TodoItem
from storage import TodoStore

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def temp_config(tmp_path: Path) -> Generator[Config, None, None]:
    """Provides a temporary config directory and mocks Config to use it."""
    config_dir = tmp_path / ".config" / "todo-cli"
    config_dir.mkdir(parents=True, exist_ok=True)
    with patch.dict(os.environ, {"TODO_CONFIG_DIR": str(config_dir)}):
        yield Config(config_dir=config_dir)


@pytest.fixture
def mock_sheet() -> MagicMock:
    sheet = MagicMock()
    # Mock spreadsheet url for the 'url' command
    sheet.spreadsheet.url = "https://docs.google.com/spreadsheets/d/test"
    return sheet


@pytest.fixture
def mock_store(temp_config: Config, mock_sheet: MagicMock) -> TodoStore:
    store = TodoStore(temp_config)
    store._sheet = mock_sheet
    return store


# ── Model Tests ───────────────────────────────────────────────────────────────


def test_todo_item_creation() -> None:
    item = TodoItem(id=1, task="Test", status="pending", created="2023-01-01 10:00")
    assert item.id == 1
    assert item.task == "Test"
    assert item.to_row() == [1, "Test", "pending", "2023-01-01 10:00", ""]


def test_todo_item_from_dict() -> None:
    data = {
        "ID": "1",
        "Task": "Test",
        "Status": "done",
        "Created": "2023-01-01",
        "Description": "Desc",
    }
    item = TodoItem.from_dict(data)
    assert item is not None
    assert item.id == 1
    assert item.description == "Desc"

    # Test invalid data
    assert TodoItem.from_dict({"Wrong": "Data"}) is None


# ── Configuration Tests ───────────────────────────────────────────────────────


def test_config_load_save(tmp_path: Path) -> None:
    cfg = Config(config_dir=tmp_path)
    cfg.set_spreadsheet_id("test-id")
    assert cfg.get_spreadsheet_id() == "test-id"

    # Reload
    cfg2 = Config(config_dir=tmp_path)
    assert cfg2.get_spreadsheet_id() == "test-id"


def test_config_corrupted_json(tmp_path: Path) -> None:
    cfg = Config(config_dir=tmp_path)
    cfg.config_file.write_text("{invalid json")
    assert cfg.load() == {}


# ── Storage & Logic Tests ─────────────────────────────────────────────────────


def test_sync_sorting_and_indexing(temp_config: Config, mock_sheet: MagicMock) -> None:
    store = TodoStore(temp_config)
    store._sheet = mock_sheet

    # Create items out of order and with mixed status
    items = [
        TodoItem(id=99, task="D2", status="done", created="2023-01-02 10:00"),
        TodoItem(id=1, task="P2", status="pending", created="2023-01-02 09:00"),
        TodoItem(id=5, task="D1", status="done", created="2023-01-01 10:00"),
        TodoItem(id=2, task="P1", status="pending", created="2023-01-01 09:00"),
    ]

    store.sync(items)

    # Check what was passed to update
    args, kwargs = mock_sheet.update.call_args
    data = kwargs["values"]

    # Headers should be first
    assert data[0] == TodoStore.HEADERS

    # Pending should come before Done
    # Within status, sorted by creation date
    assert data[1][1] == "P1"  # ID 1
    assert data[1][0] == 1
    assert data[2][1] == "P2"  # ID 2
    assert data[2][0] == 2
    assert data[3][1] == "D1"  # ID 3
    assert data[3][0] == 3
    assert data[4][1] == "D2"  # ID 4
    assert data[4][0] == 4


def test_add_todo_logic(mock_store: TodoStore, mock_sheet: MagicMock) -> None:
    mock_sheet.get_all_records.return_value = []

    mock_store.add("New Task", "Description")

    # Verify sync was called with the new item
    mock_sheet.update.assert_called_once()
    data = mock_sheet.update.call_args[1]["values"]
    assert data[1][1] == "New Task"
    assert data[1][4] == "Description"


def test_mark_done_logic(mock_store: TodoStore, mock_sheet: MagicMock) -> None:
    mock_sheet.get_all_records.return_value = [
        {
            "ID": 1,
            "Task": "T1",
            "Status": "pending",
            "Created": "2023-01-01 10:00",
            "Description": "",
        }
    ]

    mock_store.mark_done([1])

    data = mock_sheet.update.call_args[1]["values"]
    assert data[1][2] == "done"


def test_delete_logic(mock_store: TodoStore, mock_sheet: MagicMock) -> None:
    mock_sheet.get_all_records.return_value = [
        {
            "ID": 1,
            "Task": "T1",
            "Status": "pending",
            "Created": "2023-01-01 10:00",
            "Description": "",
        },
        {
            "ID": 2,
            "Task": "T2",
            "Status": "pending",
            "Created": "2023-01-01 11:00",
            "Description": "",
        },
    ]

    mock_store.delete([1])

    data = mock_sheet.update.call_args[1]["values"]
    assert len(data) == 2  # Header + 1 item
    assert data[1][1] == "T2"


def test_cli_delete_skip_completed(runner: CliRunner, mock_store: TodoStore) -> None:
    # Set up records: 1 done, 1 pending
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Done", "Status": "done", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Pend", "Status": "pending", "Created": "2023-01-01 11:00"},
    ]

    with patch.object(mock_store, "delete", wraps=mock_store.delete) as mock_del:
        res = runner.invoke(cli, ["delete", "1", "2"], input="s\n", obj=mock_store)
        assert "Warning: 1 selected tasks are completed." in res.output
        assert "Deleted: Pend" in res.output

        # Verify store.delete was called ONLY with [2]
        mock_del.assert_called_once_with([2])


def test_cli_delete_all_including_completed(
    runner: CliRunner, mock_store: TodoStore
) -> None:
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Done", "Status": "done", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Pend", "Status": "pending", "Created": "2023-01-01 11:00"},
    ]

    with patch.object(mock_store, "delete", wraps=mock_store.delete) as mock_del:
        # Choose 'a' for All
        res = runner.invoke(cli, ["delete", "1", "2"], input="a\n", obj=mock_store)
        assert "Warning: 1 selected tasks are completed." in res.output
        assert "Deleted: Done" in res.output
        assert "Deleted: Pend" in res.output

        # Verify store.delete was called with both [1, 2]
        args, _ = mock_del.call_args
        assert set(args[0]) == {1, 2}


# ── CLI Functionality Tests ───────────────────────────────────────────────────


def test_cli_list_filters(runner: CliRunner, mock_store: TodoStore) -> None:
    mock_store.sheet.get_all_records.return_value = [
        {
            "ID": 1,
            "Task": "PendingTask",
            "Status": "pending",
            "Created": "2023-01-01 10:00",
        },
        {
            "ID": 2,
            "Task": "DoneTask",
            "Status": "done",
            "Created": "2023-01-01 11:00",
        },
    ]

    # Default: show pending
    res = runner.invoke(cli, ["list"], obj=mock_store)
    assert "PendingTask" in res.output
    assert "DoneTask" not in res.output

    # All
    res = runner.invoke(cli, ["list", "-a"], obj=mock_store)
    assert "PendingTask" in res.output
    assert "DoneTask" in res.output

    # Completed only
    res = runner.invoke(cli, ["list", "-d"], obj=mock_store)
    assert "PendingTask" not in res.output
    assert "DoneTask" in res.output


def test_cli_show(runner: CliRunner, mock_store: TodoStore) -> None:
    mock_store.sheet.get_all_records.return_value = [
        {
            "ID": 1,
            "Task": "Task 1",
            "Status": "pending",
            "Created": "2023-01-01 10:00",
            "Description": "My Desc",
        }
    ]
    res = runner.invoke(cli, ["show", "1"], obj=mock_store)
    assert "Task #1: Task 1" in res.output
    assert "My Desc" in res.output

    # Missing ID
    res = runner.invoke(cli, ["show", "99"], obj=mock_store)
    assert "No task found with ID 99" in res.output


def test_cli_config_cmd(
    runner: CliRunner, temp_config: Config, mock_store: TodoStore
) -> None:
    res = runner.invoke(cli, ["config", "--spreadsheet-id", "new-id"], obj=mock_store)
    assert "Spreadsheet ID set to: new-id" in res.output
    assert temp_config.get_spreadsheet_id() == "new-id"


# ── Interactive Mode Tests ────────────────────────────────────────────────────


def test_interactive_basic_flow(runner: CliRunner, mock_store: TodoStore) -> None:
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Ex", "Status": "pending", "Created": "2023-01-01 10:00"}
    ]
    # Test implicit add, list, help, exit
    inputs = [
        "h",  # help
        "l",  # list
        "New Task",  # implicit add
        "exit",  # quit
    ]
    res = runner.invoke(
        cli, ["interactive"], input="\n".join(inputs) + "\n", obj=mock_store
    )
    assert res.exit_code == 0
    assert "Available Commands:" in res.output
    assert "Ex" in res.output
    assert "Added: New Task" in res.output


def test_interactive_done_delete(runner: CliRunner, mock_store: TodoStore) -> None:
    mock_store.sheet.get_all_records.return_value = [
        {
            "ID": 1,
            "Task": "T1",
            "Status": "pending",
            "Created": "2023-01-01 10:00",
        },
        {"ID": 2, "Task": "T2", "Status": "pending", "Created": "2023-01-01 11:00"},
    ]
    # Test 'done' and 'delete' commands
    inputs = [
        "done 1",
        "y",  # confirmation
        "delete 2",
        "y",  # confirmation
        "exit",
    ]
    res = runner.invoke(
        cli, ["interactive"], input="\n".join(inputs) + "\n", obj=mock_store
    )
    assert res.exit_code == 0
    assert "Marked #1 as done" in res.output
    assert "Deleted: T2" in res.output


# ── Resiliency & Error Handling Tests ─────────────────────────────────────────


def test_resiliency_missing_creds(runner: CliRunner, tmp_path: Path) -> None:
    """Test behavior when credentials.json is missing."""
    config_dir = tmp_path / "no_creds"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = Config(config_dir=config_dir)
    store = TodoStore(config)

    res = runner.invoke(cli, ["list"], obj=store)
    assert "Error: credentials.json not found" in res.output
    assert res.exit_code != 0


def test_resiliency_api_error_get_all(runner: CliRunner, mock_store: TodoStore) -> None:
    """Test behavior when Google API returns an error during get_all."""
    mock_store.sheet.get_all_records.side_effect = Exception("API Down")
    res = runner.invoke(cli, ["list"], obj=mock_store)
    assert "Error fetching todos: API Down" in res.output
    assert "Summary:" in res.output


def test_resiliency_sync_failure(runner: CliRunner, mock_store: TodoStore) -> None:
    """Test behavior when sync fails."""
    mock_store.sheet.get_all_records.return_value = []
    mock_store.sheet.update.side_effect = Exception("Quota exceeded")

    res = runner.invoke(cli, ["add", "Fail Task"], obj=mock_store)
    assert "Error syncing to Google Sheets: Quota exceeded" in res.output


def test_resiliency_spreadsheet_not_found(temp_config: Config) -> None:
    """Test auto-creation when spreadsheet is missing."""
    with patch("gspread.authorize") as mock_auth:
        gc = MagicMock()
        mock_auth.return_value = gc
        gc.open_by_key.side_effect = gspread.SpreadsheetNotFound

        new_ss = MagicMock()
        new_ss.id = "newly-created-id"
        new_ss.url = "http://new-ss"
        gc.create.return_value = new_ss

        store = TodoStore(temp_config)
        with patch.object(store, "get_credentials", return_value=MagicMock()):
            _ = store.sheet
            assert temp_config.get_spreadsheet_id() == "newly-created-id"
            gc.create.assert_called_with("Todo List")


# ── Performance (Batching) ────────────────────────────────────────────────────


def test_performance_sync_called_once(mock_store: TodoStore) -> None:
    """Ensure we only call update once during a sync operation."""
    mock_store.sheet.get_all_records.return_value = []

    store = mock_store
    store.add("Batch test")
    assert store.sheet.update.call_count == 1

    store.sheet.get_all_records.return_value = [
        {
            "ID": 1,
            "Task": "T1",
            "Status": "pending",
            "Created": "...",
            "Description": "",
        }
    ]
    store.mark_done([1])
    assert store.sheet.update.call_count == 2
