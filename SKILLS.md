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

- **Interactive Mode**: A menu-driven session that automatically lists tasks on launch, supports `l` alias with `-a` (all) and `-d` (done) flags, and features an instant `h` key prompt for help.
- **List Todos**: View pending or all tasks, complete with color-coded age tracking (green <3d, yellow 3-7d, red >7d) and a status summary count.
- **Add Task**: Create new tasks, with the option to attach detailed descriptions using `-m`.
- **Show Task Details**: Use `show <id>` to view full details of a task, revealing its hidden description.
- **Complete Task**: Mark tasks as done.
- **Delete Task**: Remove tasks.
- **View URL**: Get the direct link to the Google Spreadsheet.

## Structure

- `todo-cli/`: Source directory for the skill.
- `todo-cli.skill`: Packaged skill file ready for installation.
- `todo.py`: The original CLI script.
