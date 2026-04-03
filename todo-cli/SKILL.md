---
name: todo-cli
description: Manage a todo list backed by Google Sheets. Use this skill to list, add, mark as done, or delete tasks from the user's todo list.
---
# todo-cli

This skill provides a command-line interface to manage tasks stored in a Google Spreadsheet.

## Workflow

1. **List Todos**: Use `todo list` (or `todo l`) to see pending tasks, showing their age and a summary. Use `todo l -a` for all tasks.
2. **Show Task Details**: Use `todo show <id>` to view full details of a task, including its description.
3. **Add Task**: Use `todo add "Task name"` to create a new task. You can optionally add a detailed description with `-m "Description text"`.
4. **Complete Task**: Use `todo done <id>` to mark a task as finished.
5. **Delete Task**: Use `todo delete <id>` to remove a task.
6. **View URL**: Use `todo url` to get the spreadsheet link.
7. **Interactive Mode**: Use `todo interactive` to enter a persistent, menu-driven session.

## Configuration

Requires a Google OAuth `credentials.json` at `~/.config/todo-cli/credentials.json`.
The tool automatically creates a "Todo List" spreadsheet on first use if not configured.

## Usage Details

The skill uses the `todo.py` script located in the `scripts/` directory.

### Commands
- `python3 scripts/todo.py list` or `python3 scripts/todo.py l`
- `python3 scripts/todo.py l -a`
- `python3 scripts/todo.py show <id>`
- `python3 scripts/todo.py add "<task>" [-m "<description>"]`
- `python3 scripts/todo.py done <id>`
- `python3 scripts/todo.py delete <id>`
- `python3 scripts/todo.py url`
- `python3 scripts/todo.py interactive`
- `python3 scripts/todo.py config`
