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
- `todo.py`: Lightweight entry point for the CLI.
- `cli.py`: Contains Click command definitions and the interactive loop logic.
- `models.py`: Defines the `TodoItem` dataclass and row conversion logic.
- `storage.py`: Encapsulates Google Sheets API interaction and synchronization.
- `config.py`: Manages configuration files, directories, and environment variable overrides.
- `test_todo.py`: Comprehensive test suite covering all modules with extensive mocking.
- `pyproject.toml`: Project metadata, dependencies, and script entry points.

## Architecture & Data Flow
The project uses a modular architecture for better maintainability:

1. **`TodoItem` (models.py)**: Type-safe representation of tasks.
2. **`Config` (config.py)**: Manages `~/.config/todo-cli/` and supports `TODO_CONFIG_DIR` overrides.
3. **`TodoStore` (storage.py)**: Handles authentication, batch updates, and re-indexing.
   - **Authentication**: Lazy OAuth2 flow with `credentials.json`.
   - **Optimization**: Uses `clear()` and `update()` for efficient full-sheet synchronization.
   - **Resiliency**: Robust error handling for API failures and corrupted config files.
   - **Sorting**: Automatically sorts tasks (Pending > Done) and re-indexes IDs (1..N) after every write.

## Core Features
- **Smart Deletion**: Specifically warns if completed tasks are selected for deletion, offering to skip them and only delete pending tasks.
- **Automatic Listing**: Displays pending tasks and a status summary on launch.
- **Task Summary**: Concise status overview (Pending/Completed/Total).
- **Task Descriptions**: Add detailed notes via `--desc` or `-m`.
- **Task Details**: `show <id>` command for full details including hidden descriptions.
- **Color-coded Age**: Displays task age in days: Green (<3d), Yellow (3-7d), Red (>7d).
- **Interactive Mode**: Menu-driven session with implicit adding and `shlex` parsing.
- **Batch Operations**: Support for multiple IDs in `done` and `delete`.


## Development Guidelines
- **Python Style**: Adhere to PEP 8. Use clear, descriptive variable names and robust type hinting.
- **Testing**: Every functional change must be accompanied by a test in `test_todo.py`. Use mocking to avoid hitting the live Google API during tests.
- **Performance**: Always prefer batch operations over sequential API calls to minimize network overhead and avoid rate limiting.

## Setup for Development
1. Install in editable mode: `pip install -e .`
2. Install test dependencies: `pip install pytest`
3. Run the test suite: `pytest test_todo.py`
4. Run the interactive CLI: `python todo.py interactive`
