# todo-cli

A command-line todo list manager backed by Google Sheets.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Sheets API** and **Google Drive API**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
5. Choose **Desktop app**, give it a name, click Create
6. Download the JSON file and save it to:
   ```
   ~/.config/todo-cli/credentials.json
   ```

### 3. First run

On the first command, a browser window will open for Google OAuth login.
After login, a token is saved to `~/.config/todo-cli/token.json` for future use.

A new Google Sheet called **"Todo List"** will be created automatically in your Drive.
To use an existing sheet instead:

```bash
python todo.py config --spreadsheet-id <your-sheet-id>
```

## Usage

```bash
# Start an interactive session (lists pending tasks automatically)
python todo.py interactive

# List pending todos (shows age and status summary)
python todo.py list
# Or use the short alias
python todo.py l

# List all todos including completed
python todo.py l -a

# Add a new todo
python todo.py add "Buy groceries"

# Add a new todo with a description
python todo.py add "Buy groceries" -m "Milk, eggs, and bread"

# Show detailed information for a task (including description)
python todo.py show 1

# Mark item #3 as done
python todo.py done 3

# Delete item #5 (with confirmation prompt)
python todo.py delete 5

# Delete without confirmation
python todo.py delete 5 --yes

# Show current config
python todo.py config
```

## Optional: install as a global command

```bash
pip install --editable .
# then use: todo list, todo add "...", etc.
```

Create a `setup.py` or `pyproject.toml` if you want this installed as `todo`.
