# `todo-cli` Project Context

A command-line todo list manager that uses Google Sheets as a persistent backend.

## Tech Stack
- **Language**: Python 3.9+
- **CLI Framework**: `click`
- **Google Sheets API**: `gspread`
- **Authentication**: `google-auth`, `google-auth-oauthlib` (OAuth2 Desktop Flow)
- **Formatting**: `tabulate` (for CLI tables)

## Project Structure
- `todo.py`: The main script containing all CLI commands and Google Sheets interaction logic.
- `pyproject.toml`: Project metadata, dependencies, and the `todo` console script entry point.
- `requirements.txt`: List of Python dependencies for easy installation.
- `README.md`: Setup and usage instructions for users.

## Architecture & Data Flow
1. **Configuration**: All local state (OAuth tokens, credentials, and app config) is stored in `~/.config/todo-cli/`.
2. **Authentication**: Uses a `credentials.json` (OAuth Client ID) to initiate an authorization flow, saving a `token.json` for subsequent sessions.
3. **Google Sheets**: 
   - Each user has a "Todo List" spreadsheet.
   - Tasks are stored in a worksheet named "Todos" with headers: `ID`, `Task`, `Status`, `Created`.
   - `ID` values are auto-incremented based on the current list.

## Development Guidelines
- **Python Style**: Adhere to PEP 8. Use clear, descriptive variable names.
- **CLI Design**: Continue using `click` for command and option definitions.
- **Error Handling**: Gracefully handle missing credentials and network issues with user-friendly messages.
- **Google API Usage**: Minimize API calls where possible (e.g., fetch all rows once for listing/searching).

## Setup for Development
1. Install in editable mode: `pip install -e .`
2. Ensure `~/.config/todo-cli/credentials.json` exists for authentication.
3. Run tests or the CLI directly: `python todo.py list`
