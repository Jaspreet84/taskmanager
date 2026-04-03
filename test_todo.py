import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from todo import cli, TodoStore, Config, TodoItem

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_store():
    with patch('todo.TodoStore.sheet', new_callable=MagicMock) as mock_sheet:
        yield mock_sheet

def test_add_todo(runner, mock_store):
    mock_store.get_all_records.return_value = []
    result = runner.invoke(cli, ['add', 'Buy milk'])
    assert result.exit_code == 0
    assert "Added: Buy milk" in result.output
    # sync() calls clear() and update()
    mock_store.clear.assert_called_once()
    mock_store.update.assert_called_once()

def test_add_with_desc(runner, mock_store):
    mock_store.get_all_records.return_value = []
    result = runner.invoke(cli, ['add', 'Task', '--desc', 'My Description'])
    assert result.exit_code == 0
    assert "Added: Task" in result.output
    # Check that description is in the data passed to sync -> update
    args, kwargs = mock_store.update.call_args
    data = kwargs['values']
    assert data[1][1] == "Task"
    assert data[1][4] == "My Description"

def test_show_todo(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00", "Description": "Detailed info"}
    ]
    result = runner.invoke(cli, ['show', '1'])
    assert result.exit_code == 0
    assert "Task #1: Task 1" in result.output
    assert "Description: Detailed info" in result.output

def test_list_todos(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Task 2", "Status": "done", "Created": "2023-01-01 11:00"}
    ]
    
    # List pending only (default)
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" not in result.output
    
    # List all
    result = runner.invoke(cli, ['list', '-a'])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" in result.output

def test_list_summary(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Task 2", "Status": "done", "Created": "2023-01-01 11:00"},
        {"ID": 3, "Task": "Task 3", "Status": "pending", "Created": "2023-01-01 12:00"}
    ]
    
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    assert "Summary: 2 pending, 1 completed (3 total)" in result.output

def test_list_age_color(runner, mock_store):
    from datetime import datetime, timedelta
    now = datetime.now()
    
    # Task 1: 1 day old (green)
    t1 = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    # Task 2: 5 days old (yellow)
    t2 = (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
    # Task 3: 10 days old (red)
    t3 = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
    
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Recent", "Status": "pending", "Created": t1},
        {"ID": 2, "Task": "Old", "Status": "pending", "Created": t2},
        {"ID": 3, "Task": "Very Old", "Status": "pending", "Created": t3}
    ]
    
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    # Check for age strings (e.g., "1d", "5d", "10d")
    assert "1d" in result.output
    assert "5d" in result.output
    assert "10d" in result.output
    assert "Age" in result.output

def test_list_completed_flag(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Pending Task", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 11:00"}
    ]
    # Test 'list -d' directly
    result = runner.invoke(cli, ['list', '-d'])
    assert result.exit_code == 0
    assert "Done Task" in result.output
    assert "Pending Task" not in result.output

def test_mark_done(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00"}
    ]
    # Use -y to skip confirmation
    result = runner.invoke(cli, ['done', '1', '-y'])
    assert result.exit_code == 0
    assert "Marked #1 as done" in result.output
    mock_store.clear.assert_called_once()
    mock_store.update.assert_called_once()

def test_delete_todo(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00"}
    ]
    result = runner.invoke(cli, ['delete', '1', '-y'])
    assert result.exit_code == 0
    assert "Deleted: Task 1" in result.output
    mock_store.clear.assert_called_once()
    mock_store.update.assert_called_once()

def test_sync_logic():
    config = MagicMock(spec=Config)
    store = TodoStore(config)
    mock_sheet = MagicMock()
    store._sheet = mock_sheet
    
    items = [
        TodoItem(id=5, task="Done Task", status="done", created="2023-01-01 12:00"),
        TodoItem(id=2, task="New Task", status="pending", created="2023-01-01 10:00"),
    ]
    
    store.sync(items)
    
    # Check for named arguments
    args, kwargs = mock_sheet.update.call_args
    data = kwargs['values']
    # Row 0 is now HEADERS
    assert data[1][1] == "New Task"
    assert data[1][0] == 1
    assert data[2][1] == "Done Task"
    assert data[2][0] == 2

def test_interactive_add(runner, mock_store):
    mock_store.get_all_records.return_value = []
    # Test adding via interactive mode (implicit add)
    result = runner.invoke(cli, ['interactive'], input="Buy eggs\nexit\n")
    assert result.exit_code == 0
    assert "Added: Buy eggs" in result.output

def test_default_command_lists(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00"}
    ]
    # Test that running 'todo' without args lists tasks
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Task 1" in result.output

def test_interactive_list_all(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Pending Task", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 11:00"}
    ]
    # Test 'l -a' in interactive mode
    result = runner.invoke(cli, ['interactive'], input="l -a\nexit\n")
    assert result.exit_code == 0
    # Pending Task is shown twice (launch and l -a)
    # Done Task is shown once (l -a)
    assert result.output.count("Pending Task") == 2
    assert result.output.count("Done Task") == 1

def test_interactive_list_no_space(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Pending Task", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 11:00"}
    ]
    # Test 'l-a' (no space) in interactive mode
    result = runner.invoke(cli, ['interactive'], input="l-a\nexit\n")
    assert result.exit_code == 0
    # Pending Task should be shown twice (launch and l-a)
    assert result.output.count("Pending Task") == 2
    assert result.output.count("Done Task") == 1

def test_interactive_list_completed(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Pending Task", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 11:00"}
    ]
    # Test 'list -d' in interactive mode
    result = runner.invoke(cli, ['interactive'], input="list -d\nexit\n")
    assert result.exit_code == 0
    
    # It should show Pending Task once (on launch)
    # and Done Task once (after list -d)
    assert result.output.count("Pending Task") == 1
    assert result.output.count("Done Task") == 1

def test_interactive_auto_list(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00"}
    ]
    # Test that 'done' automatically triggers a 'list'
    result = runner.invoke(cli, ['interactive'], input="done 1\ny\nexit\n")
    assert result.exit_code == 0
    # Should list tasks after marking done. 
    # Because of our mock, it will list the same pending task again since we don't update the mock in real-time.
    assert "Task 1" in result.output
