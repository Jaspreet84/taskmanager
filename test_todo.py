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
    # Initial call for next_id
    # Second call for reindex
    mock_store.get_all_records.side_effect = [
        [], # for next_id
        [{"ID": 1, "Task": "Buy milk", "Status": "pending", "Created": "2023-01-01 10:00"}] # for reindex
    ]
    result = runner.invoke(cli, ['add', 'Buy milk'])
    assert result.exit_code == 0
    assert "Added: Buy milk" in result.output
    mock_store.append_row.assert_called_once()
    mock_store.update.assert_called_once()

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
    result = runner.invoke(cli, ['list', '--all'])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" in result.output

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
    mock_store.batch_update.assert_called_once()

def test_delete_todo(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Task 1", "Status": "pending", "Created": "2023-01-01 10:00"}
    ]
    result = runner.invoke(cli, ['delete', '1', '-y'])
    assert result.exit_code == 0
    assert "Deleted: Task 1" in result.output
    mock_store.delete_rows.assert_called_once_with(2)

def test_reindex_logic():
    config = MagicMock(spec=Config)
    store = TodoStore(config)
    mock_sheet = MagicMock()
    store._sheet = mock_sheet
    
    mock_sheet.get_all_records.return_value = [
        {"ID": 5, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 12:00"},
        {"ID": 2, "Task": "New Task", "Status": "pending", "Created": "2023-01-01 10:00"},
    ]
    
    store.reindex()
    
    # Check for named arguments
    args, kwargs = mock_sheet.update.call_args
    data = kwargs['values']
    assert data[0][1] == "New Task"
    assert data[0][0] == 1
    assert data[1][1] == "Done Task"
    assert data[1][0] == 2

def test_interactive_add(runner, mock_store):
    mock_store.get_all_records.return_value = []
    # Test adding via interactive mode (implicit add)
    result = runner.invoke(cli, ['interactive'], input="Buy eggs\nexit\n")
    assert result.exit_code == 0
    assert "Added: Buy eggs" in result.output

def test_interactive_list_completed(runner, mock_store):
    mock_store.get_all_records.return_value = [
        {"ID": 1, "Task": "Pending Task", "Status": "pending", "Created": "2023-01-01 10:00"},
        {"ID": 2, "Task": "Done Task", "Status": "done", "Created": "2023-01-01 11:00"}
    ]
    # Test 'list -d' in interactive mode
    result = runner.invoke(cli, ['interactive'], input="list -d\nexit\n")
    assert result.exit_code == 0
    assert "Done Task" in result.output
    assert "Pending Task" not in result.output

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
