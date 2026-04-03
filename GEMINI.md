# `todo-cli` Project Context

A command-line todo list manager that uses Google Sheets as a persistent backend.

## Tech Stack
- **Language**: Python 3.9+
- **CLI Framework**: `click`
- **Google Sheets API**: `gspread`
- **Authentication**: `google-auth`, `google-auth-oauthlib` (OAuth2 Desktop Flow)
- **Formatting**: `tabulate` (for CLI tables)
- **Testing**: `pytest` with `unittest.mock`

## Project Structure
- `todo.py`: The core implementation containing the modular architecture and CLI commands.
- `test_todo.py`: Comprehensive test suite for CLI and storage logic (uses mocking).
- `pyproject.toml`: Modern project metadata, dependencies, and script entry points.
- `requirements.txt`: Python dependencies.
- `README.md`: Setup and usage instructions.
- `SKILLS.md`: Documentation for the packaged Gemini CLI skill.
- `todo-cli/`: Source directory for the packaged skill.
- `todo-cli.skill`: Distributable Gemini CLI skill package.

## Architecture & Data Flow
The project uses a clean, modular architecture:

1. **`TodoItem` (Dataclass)**: Provides type-safe representation of tasks.
2. **`Config` (Class)**: Manages local configuration (`~/.config/todo-cli/`), including OAuth tokens and spreadsheet IDs.
3. **`TodoStore` (Class)**: Encapsulates all persistence logic.
   - **Authentication**: Handles lazy OAuth2 flow.
   - **Optimization**: Uses `batch_update()` for efficient cell writes and `batch_clear()` for resets.
   - **Robustness**: `from_dict()` gracefully handles corrupted records or misplaced headers. `reindex()` ensures sheet integrity by clearing and overwriting from A1 with fresh headers.
   - **Sorting & Reindexing**: Automatically sorts tasks (Pending > Done) and resets IDs to 1..N after every write to maintain a clean list.

## Core Features
- **Automatic Listing**: Automatically displays pending tasks and a status summary when the tool is launched without arguments or when starting an interactive session.
- **Task Summary**: Provides a concise summary of tasks by status (e.g., "Summary: 2 pending, 1 completed (3 total)") at the end of every list output.
- **Task Description**: Ability to add detailed descriptions to tasks using the `--desc` or `-m` flag during creation.
- **Task Details**: A dedicated `show <id>` command to view full task details, including the description, which remains hidden in the general list view.
- **Task Age Display**: Shows the age of each task in days. Age is color-coded for quick visual assessment: Green (< 3 days), Yellow (3-7 days), and Red (> 7 days).
- **Interactive Mode**: A menu-driven session with implicit task adding, command parsing (via `shlex`), and automatic status re-listing. Supports a concise "press h for help" prompt with instant 'h' key detection. Commands include `l` for listing with `-a` (all) and `-d` (done) flags.
- **Batch Operations**: Support for multiple IDs in `done` and `delete` commands.
- **Custom Views**: List tasks by status using flags like `-a` for all tasks and `-d` for completed tasks.

## Development Guidelines
- **Python Style**: Adhere to PEP 8. Use clear, descriptive variable names and robust type hinting.
- **Testing**: Every functional change must be accompanied by a test in `test_todo.py`. Use mocking to avoid hitting the live Google API during tests.
- **Performance**: Always prefer batch operations over sequential API calls to minimize network overhead and avoid rate limiting.

## Setup for Development
1. Install in editable mode: `pip install -e .`
2. Install test dependencies: `pip install pytest`
3. Run the test suite: `pytest test_todo.py`
4. Run the interactive CLI: `python todo.py interactive`
