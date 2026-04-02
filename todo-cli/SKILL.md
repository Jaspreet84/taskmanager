---
name: todo-cli
description: Manage a todo list backed by Google Sheets. Use this skill to list, add, mark as done, or delete tasks from the user's todo list.
---
# todo-cli

This skill provides a command-line interface to manage tasks stored in a Google Spreadsheet.

## Workflow

1. **List Todos**: Use `todo list` to see pending tasks or `todo list --all` for all tasks.
2. **Add Task**: Use `todo add "Task description"` to create a new task.
3. **Complete Task**: Use `todo done <id>` to mark a task as finished.
4. **Delete Task**: Use `todo delete <id>` to remove a task.
5. **View URL**: Use `todo url` to get the spreadsheet link.

## Configuration

Requires a Google OAuth `credentials.json` at `~/.config/todo-cli/credentials.json`.
The tool automatically creates a "Todo List" spreadsheet on first use if not configured.

## Usage Details

The skill uses the `todo.py` script located in the `scripts/` directory.

### Commands
- `python3 scripts/todo.py list`
- `python3 scripts/todo.py list --all`
- `python3 scripts/todo.py add "<task>"`
- `python3 scripts/todo.py done <id>`
- `python3 scripts/todo.py delete <id>`
- `python3 scripts/todo.py url`
- `python3 scripts/todo.py config`
