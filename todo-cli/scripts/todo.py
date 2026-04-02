#!/usr/bin/env python3
"""Refactored CLI todo list manager backed by Google Sheets."""

import json
import sys
import shlex
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

import click
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tabulate import tabulate

# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class TodoItem:
    id: int
    task: str
    status: str
    created: str

    @classmethod
    def from_dict(cls, data: Dict) -> "TodoItem":
        return cls(
            id=int(data["ID"]),
            task=data["Task"],
            status=data["Status"],
            created=data["Created"]
        )

    def to_row(self) -> List:
        return [self.id, self.task, self.status, self.created]

# ── Configuration ─────────────────────────────────────────────────────────────

class Config:
    def __init__(self):
        self.dir = Path.home() / ".config" / "todo-cli"
        self.token_file = self.dir / "token.json"
        self.creds_file = self.dir / "credentials.json"
        self.config_file = self.dir / "config.json"
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]
        self.ensure_dir()

    def ensure_dir(self):
        self.dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict:
        if self.config_file.exists():
            return json.loads(self.config_file.read_text())
        return {}

    def save(self, data: Dict):
        self.config_file.write_text(json.dumps(data, indent=2))

    def get_spreadsheet_id(self) -> Optional[str]:
        return self.load().get("spreadsheet_id")

    def set_spreadsheet_id(self, spreadsheet_id: str):
        data = self.load()
        data["spreadsheet_id"] = spreadsheet_id
        self.save(data)

# ── Storage Layer ─────────────────────────────────────────────────────────────

class TodoStore:
    SHEET_NAME = "Todos"
    HEADERS = ["ID", "Task", "Status", "Created"]

    def __init__(self, config: Config):
        self.config = config
        self._sheet = None

    def get_credentials(self):
        if not self.config.creds_file.exists():
            click.echo(f"Error: credentials.json not found at {self.config.creds_file}", err=True)
            sys.exit(1)

        creds = None
        if self.config.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.config.token_file), self.config.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.config.creds_file), self.config.scopes)
                creds = flow.run_local_server(port=0)
            self.config.token_file.write_text(creds.to_json())
        return creds

    @property
    def sheet(self):
        if self._sheet is None:
            creds = self.get_credentials()
            gc = gspread.authorize(creds)
            spreadsheet_id = self.config.get_spreadsheet_id()
            
            spreadsheet = None
            if spreadsheet_id:
                try:
                    spreadsheet = gc.open_by_key(spreadsheet_id)
                except gspread.SpreadsheetNotFound:
                    pass

            if spreadsheet is None:
                spreadsheet = gc.create("Todo List")
                self.config.set_spreadsheet_id(spreadsheet.id)
                click.echo(f"Created new spreadsheet: {spreadsheet.url}")

            try:
                self._sheet = spreadsheet.worksheet(self.SHEET_NAME)
            except gspread.WorksheetNotFound:
                self._sheet = spreadsheet.add_worksheet(title=self.SHEET_NAME, rows=1000, cols=4)
                self._sheet.append_row(self.HEADERS)

            # Ensure headers
            if self._sheet.row_values(1) != self.HEADERS:
                self._sheet.insert_row(self.HEADERS, 1)
        return self._sheet

    def get_all(self) -> List[TodoItem]:
        records = self.sheet.get_all_records()
        return [TodoItem.from_dict(r) for r in records]

    def add(self, task: str):
        items = self.get_all()
        new_id = len(items) + 1
        created = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.sheet.append_row([new_id, task, "pending", created])
        self.reindex()

    def mark_done(self, ids: List[int]):
        items = self.get_all()
        updates = []
        for i, item in enumerate(items, start=2):
            if item.id in ids and item.status != "done":
                updates.append({
                    'range': f'C{i}',
                    'values': [['done']]
                })
        
        if updates:
            self.sheet.batch_update(updates)
            self.reindex()

    def delete(self, ids: List[int]):
        items = self.get_all()
        to_delete = sorted([i for i, item in enumerate(items, start=2) if item.id in ids], reverse=True)
        if to_delete:
            for row_idx in to_delete:
                self.sheet.delete_rows(row_idx)
            self.reindex()

    def reindex(self):
        items = self.get_all()
        if not items:
            # Clear range if empty
            self.sheet.batch_clear(["A2:D1000"])
            return
        
        # Sort: pending first, then by date
        items.sort(key=lambda x: (x.status == "done", x.created))
        
        new_data = []
        for i, item in enumerate(items, start=1):
            item.id = i
            new_data.append(item.to_row())
        
        # Batch update the entire range
        self.sheet.update(range_name=f"A2:D{len(new_data) + 1}", values=new_data)

# ── CLI Commands ──────────────────────────────────────────────────────────────

@click.group()
@click.pass_context
def cli(ctx):
    """Todo list manager backed by Google Sheets."""
    ctx.obj = TodoStore(Config())

@cli.command("list")
@click.option("--all", "show_all", is_flag=True, help="Include completed items.")
@click.option("--completed", "-d", "show_completed", is_flag=True, help="Show only completed items.")
@click.pass_obj
def list_todos(store: TodoStore, show_all: bool, show_completed: bool):
    """Show todo items."""
    items = store.get_all()
    if show_completed:
        items = [i for i in items if i.status == "done"]
    elif not show_all:
        items = [i for i in items if i.status != "done"]

    if not items:
        if show_completed:
            click.echo("No completed todos found.")
        else:
            click.echo("No pending todos." if not show_all else "No todos found.")
        return

    table = [
        [
            i.id,
            i.task,
            click.style("done", fg="green") if i.status == "done" else click.style("pending", fg="yellow"),
            i.created,
        ]
        for i in items
    ]
    click.echo(tabulate(table, headers=store.HEADERS, tablefmt="rounded_outline"))

@cli.command("add")
@click.argument("task")
@click.pass_obj
def add_todo(store: TodoStore, task: str):
    """Add a new todo item."""
    store.add(task)
    click.echo(f"Added: {task}")

@cli.command("done")
@click.argument("ids", type=int, nargs=-1)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def mark_done(store: TodoStore, ids: List[int], yes: bool):
    """Mark todo items as complete."""
    if not ids: return
    items = [i for i in store.get_all() if i.id in ids and i.status != "done"]
    if not items:
        click.echo("No pending todos found for given IDs.")
        return

    if not yes:
        click.confirm(f"Mark tasks {', '.join(str(i.id) for i in items)} as done?", abort=True)
    
    store.mark_done(ids)
    for i in items:
        click.echo(f"Marked #{i.id} as done: {i.task}")

@cli.command("delete")
@click.argument("ids", type=int, nargs=-1)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def delete_todo(store: TodoStore, ids: List[int], yes: bool):
    """Delete todo items."""
    if not ids: return
    items = [i for i in store.get_all() if i.id in ids]
    if not items:
        click.echo("No todos found for given IDs.")
        return

    if not yes:
        click.confirm(f"Delete tasks {', '.join(str(i.id) for i in items)}?", abort=True)
    
    store.delete(ids)
    for i in items:
        click.echo(f"Deleted: {i.task}")

@cli.command("url")
@click.pass_obj
def show_url(store: TodoStore):
    """Show the URL of the current Google Spreadsheet."""
    click.echo(store.sheet.spreadsheet.url)

@cli.command("interactive")
@click.pass_context
def interactive(ctx: click.Context):
    """Start an interactive session to manage tasks."""
    store: TodoStore = ctx.obj
    
    def print_help():
        click.echo(click.style("\nAvailable Commands:", bold=True))
        click.echo("  list [-d|--all]  - Show tasks (default: pending, -d: done, --all: both)")
        click.echo("  add <task>       - Add a new task (or just type the task)")
        click.echo("  done [ids...]    - Mark tasks as complete")
        click.echo("  delete [ids...]  - Remove tasks")
        click.echo("  url              - Show spreadsheet link")
        click.echo("  help             - Show this help message")
        click.echo("  exit/quit        - Close the session")
        click.echo("  Type 'c' or 'cancel' to abort any prompt.")

    click.echo(click.style("Welcome to the Interactive Todo Manager!", fg="cyan", bold=True))
    print_help()
    
    while True:
        try:
            line = click.prompt("> ", default="", show_default=False).strip()
        except (click.Abort, EOFError):
            click.echo("\nGoodbye!")
            break
            
        if not line: continue
        
        try:
            parts = shlex.split(line)
        except ValueError as e:
            click.echo(f"Error parsing command: {e}")
            continue

        if not parts: continue
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ["exit", "quit"]:
            click.echo("Goodbye!")
            break
        elif cmd == "help":
            print_help()
        elif cmd == "list":
            show_all = "--all" in args
            show_completed = "-d" in args or "--completed" in args
            ctx.invoke(list_todos, show_all=show_all, show_completed=show_completed)
        elif cmd == "url":
            ctx.invoke(show_url)
        elif cmd == "add":
            task = " ".join(args) or click.prompt("Enter task (or 'c')", default="", show_default=False)
            if task and task.lower() not in ["c", "cancel"]:
                ctx.invoke(add_todo, task=task)
        elif cmd in ["done", "delete"]:
            ids = [int(x) for x in args if x.isdigit()]
            if not ids:
                ctx.invoke(list_todos, show_all=False, show_completed=False)
                prompt_msg = f"Enter IDs to {cmd} (or 'c')"
                ids_input = click.prompt(prompt_msg, default="", show_default=False)
                if not ids_input or ids_input.lower() in ["c", "cancel"]:
                    continue
                ids = [int(x) for x in ids_input.split() if x.isdigit()]
            
            if ids:
                try:
                    if cmd == "done": ctx.invoke(mark_done, ids=ids, yes=False)
                    else: ctx.invoke(delete_todo, ids=ids, yes=False)
                    # Automatically list pending tasks after action
                    ctx.invoke(list_todos, show_all=False, show_completed=False)
                except (click.Abort, SystemExit): pass
        else:
            # Treat as implicit add
            ctx.invoke(add_todo, task=line)

@cli.command("config")
@click.option("--spreadsheet-id", help="Set an existing spreadsheet ID to use.")
@click.pass_obj
def configure(store: TodoStore, spreadsheet_id: str):
    """Show or update configuration."""
    if spreadsheet_id:
        store.config.set_spreadsheet_id(spreadsheet_id)
        click.echo(f"Spreadsheet ID set to: {spreadsheet_id}")
    else:
        click.echo(f"Config file:    {store.config.config_file}")
        click.echo(f"Credentials:    {store.config.creds_file}")
        click.echo(f"Spreadsheet ID: {store.config.get_spreadsheet_id() or '(not set)'}")

if __name__ == "__main__":
    cli()
