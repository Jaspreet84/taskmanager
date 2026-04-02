# `todo-cli` Skill

This directory contains a packaged Gemini CLI skill for managing a todo list via Google Sheets.

## Installation

To install this skill for the user:

```bash
gemini skills install todo-cli.skill --scope user
```

After installation, reload the skills in your interactive Gemini session:

```bash
/skills reload
```

## Features

- **List Todos**: View pending or all tasks.
- **Add Task**: Create new tasks.
- **Complete Task**: Mark tasks as done.
- **Delete Task**: Remove tasks.
- **View URL**: Get the direct link to the Google Spreadsheet.

## Structure

- `todo-cli/`: Source directory for the skill.
- `todo-cli.skill`: Packaged skill file ready for installation.
- `todo.py`: The original CLI script.
