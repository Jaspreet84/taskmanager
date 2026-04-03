"""Comprehensive test suite for todo-cli. Powered by GEMINI."""
import pytest
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

import gspread
from todo import cli
from models import TodoItem
from storage import TodoStore
from config import Config

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def temp_config(tmp_path):
    """Provides a temporary config directory and mocks Config to use it."""
    config_dir = tmp_path / ".config" / "todo-cli"
    config_dir.mkdir(parents=True)
    with patch.dict(os.environ, {"TODO_CONFIG_DIR": str(config_dir)}):
        yield Config(config_dir=config_dir)

@pytest.fixture
def mock_sheet():
    sheet = MagicMock()
    # Mock spreadsheet url for the 'url' command
    sheet.spreadsheet.url = "https://docs.google.com/spreadsheets/d/test"
    return sheet

@pytest.fixture
def mock_store(temp_config, mock_sheet):
    store = TodoStore(temp_config)
    store._sheet = mock_sheet
    return store

def test_add_todo_logic(mock_store, mock_sheet):
    mock_sheet.get_all_records.return_value = []
    
    mock_store.add("New Task", "Description")
    
    # Verify sync was called with the new item
    mock_sheet.update.assert_called_once()
    data = mock_sheet.update.call_args[1]['values']
    assert data[1][1] == "New Task"
    assert data[1][4] == "Description"

def test_mark_done_logic(mock_store, mock_sheet):
    mock_sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "T1", "Status": "pending", "Created": "2023-01-01 10:00", "Description": ""}
    ]
    
    mock_store.mark_done([1])
    
    data = mock_sheet.update.call_args[1]['values']
    assert data[1][2] == "done"

def test_delete_logic(mock_store, mock_sheet):
    mock_sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "T1", "Status": "pending", "Created": "2023-01-01 10:00", "Description": ""},
        {"ID": 2, "Task": "T2", "Status": "pending", "Created": "2023-01-01 11:00", "Description": ""}
    ]
    
    mock_store.delete([1])
    
    data = mock_sheet.update.call_args[1]['values']
    assert len(data) == 2  # Header + 1 item
    assert data[1][1] == "T2"

def test_cli_delete_skip_completed(runner, mock_store):
    # Set up records: 1 done, 1 pending
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Pending Task", "Status": "pending", "Created": "2023-01-01 11:00"}
    ]
    
    # Select both (1 and 2), choose 's' to skip completed (1)
    # This should result in only ID 2 being deleted.
    # The sync() will then fetch all records again, remove ID 2, and update the sheet.
    
    # We need to ensure that when sync() is called after delete([2]), 
    # it only sees the remaining items.
    # However, since we mock get_all_records, it will always return the same thing
    # unless we side_effect it. Let's simplify and just check the call to store.delete.
    
    with patch.object(mock_store, 'delete', wraps=mock_store.delete) as mock_del:
        res = runner.invoke(cli, ["delete", "1", "2"], input="s\n", obj=mock_store)
        assert "Warning: 1 of the selected tasks are already completed." in res.output
        assert "Deleted: Pending Task" in res.output
        
        # Verify store.delete was called ONLY with [2]
        mock_del.assert_called_once_with([2])

def test_cli_delete_all_including_completed(runner, mock_store):
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Pending Task", "Status": "pending", "Created": "2023-01-01 11:00"}
    ]
    
    with patch.object(mock_store, 'delete', wraps=mock_store.delete) as mock_del:
        # Choose 'a' for All
        res = runner.invoke(cli, ["delete", "1", "2"], input="a\n", obj=mock_store)
        assert "Warning: 1 of the selected tasks are already completed." in res.output
        assert "Deleted: Done Task" in res.output
        assert "Deleted: Pending Task" in res.output
        
        # Verify store.delete was called with both [1, 2]
        # IDs might be in a list or tuple depending on click
        args, _ = mock_del.call_args
        assert set(args[0]) == {1, 2}



# ── CLI Functionality Tests ───────────────────────────────────────────────────

def test_cli_list_filters(runner, mock_store):
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Pending", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Done", "Status": "done", "Created": "2023-01-01 11:00"}
    ]
    
    # Default: show pending
    res = runner.invoke(cli, ["list"], obj=mock_store)
    assert "Pending" in res.output
    assert "Done" not in res.output
    
    # All
    res = runner.invoke(cli, ["list", "-a"], obj=mock_store)
    assert "Pending" in res.output
    assert "Done" in res.output
    
    # Completed only
    res = runner.invoke(cli, ["list", "-d"], obj=mock_store)
    assert "Pending" not in res.output
    assert "Done" in res.output

def test_cli_show(runner, mock_store):
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00", "Description": "My Desc"}
    ]
    res = runner.invoke(cli, ["show", "1"], obj=mock_store)
    assert "Task #1: Task 1" in res.output
    assert "My Desc" in res.output
    
    # Missing ID
    res = runner.invoke(cli, ["show", "99"], obj=mock_store)
    assert "No task found with ID 99" in res.output

def test_cli_config_cmd(runner, temp_config, mock_store):
    res = runner.invoke(cli, ["config", "--spreadsheet-id", "new-id"], obj=mock_store)
    assert "Spreadsheet ID set to: new-id" in res.output
    assert temp_config.get_spreadsheet_id() == "new-id"

# ── Interactive Mode Tests ────────────────────────────────────────────────────

def test_interactive_basic_flow(runner, mock_store):
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "Existing", "Status": "pending", "Created": "2023-01-01 10:00"}
    ]
    # Test implicit add, list, help, exit
    inputs = [
        "h",           # help
        "l",           # list
        "New Task",    # implicit add
        "exit"         # quit
    ]
    res = runner.invoke(cli, ["interactive"], input="\n".join(inputs) + "\n", obj=mock_store)
    assert res.exit_code == 0
    assert "Available Commands:" in res.output
    assert "Existing" in res.output
    assert "Added: New Task" in res.output

def test_interactive_done_delete(runner, mock_store):
    mock_store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "To Finish", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "To Delete", "Status": "pending", "Created": "2023-01-01 11:00"}
    ]
    # Test 'done' and 'delete' commands
    inputs = [
        "done 1",
        "y",        # confirmation
        "delete 2",
        "y",        # confirmation
        "exit"
    ]
    res = runner.invoke(cli, ["interactive"], input="\n".join(inputs) + "\n", obj=mock_store)
    assert res.exit_code == 0
    assert "Marked #1 as done" in res.output
    assert "Deleted: To Delete" in res.output

# ── Resiliency & Error Handling Tests ─────────────────────────────────────────

def test_resiliency_missing_creds(runner, tmp_path):
    """Test behavior when credentials.json is missing."""
    config_dir = tmp_path / "no_creds"
    config_dir.mkdir()
    config = Config(config_dir=config_dir)
    store = TodoStore(config)
    
    res = runner.invoke(cli, ["list"], obj=store)
    assert "Error: credentials.json not found" in res.output
    assert res.exit_code != 0

def test_resiliency_api_error_get_all(runner, mock_store):
    """Test behavior when Google API returns an error during get_all."""
    mock_store.sheet.get_all_records.side_effect = Exception("API Down")
    res = runner.invoke(cli, ["list"], obj=mock_store)
    assert "Error fetching todos: API Down" in res.output
    assert "Summary:" in res.output

def test_resiliency_sync_failure(runner, mock_store):
    """Test behavior when sync fails."""
    mock_store.sheet.get_all_records.return_value = []
    mock_store.sheet.update.side_effect = Exception("Quota exceeded")
    
    res = runner.invoke(cli, ["add", "Fail Task"], obj=mock_store)
    assert "Error syncing to Google Sheets: Quota exceeded" in res.output

def test_resiliency_spreadsheet_not_found(temp_config):
    """Test auto-creation when spreadsheet is missing."""
    with patch('gspread.authorize') as mock_auth:
        gc = MagicMock()
        mock_auth.return_value = gc
        gc.open_by_key.side_effect = gspread.SpreadsheetNotFound
        
        new_ss = MagicMock()
        new_ss.id = "newly-created-id"
        new_ss.url = "http://new-ss"
        gc.create.return_value = new_ss
        
        store = TodoStore(temp_config)
        with patch.object(store, 'get_credentials', return_value=MagicMock()):
            sheet = store.sheet
            assert temp_config.get_spreadsheet_id() == "newly-created-id"
            gc.create.assert_called_with("Todo List")

# ── Performance (Batching) ────────────────────────────────────────────────────

def test_performance_sync_called_once(mock_store):
    """Ensure we only call update once during a sync operation."""
    mock_store.sheet.get_all_records.return_value = []
    
    store = mock_store
    store.add("Batch test")
    assert store.sheet.update.call_count == 1
    
    store.sheet.get_all_records.return_value = [
        {"ID": 1, "Task": "T1", "Status": "pending", "Created": "...", "Description": ""}
    ]
    store.mark_done([1])
    assert store.sheet.update.call_count == 2

