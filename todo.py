#!/usr/bin/env python3
"""Refactored CLI todo list manager backed by Google Sheets."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import click
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tabulate import tabulate

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

    def get_all(self) -> List[Dict]:
        return self.sheet.get_all_records()

    def add(self, task: str):
        rows = self.get_all()
        new_id = len(rows) + 1
        created = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.sheet.append_row([new_id, task, "pending", created])
        self.reindex()

    def mark_done(self, ids: List[int]):
        records = self.get_all()
        # Find row indices (1-based, header is 1)
        updates = []
        for i, row in enumerate(records, start=2):
            if int(row["ID"]) in ids and row["Status"] != "done":
                updates.append({
                    'range': f'C{i}',
                    'values': [['done']]
                })
        
        if updates:
            self.sheet.batch_update(updates)
            self.reindex()

    def delete(self, ids: List[int]):
        records = self.get_all()
        # Delete in reverse to keep indices valid during loop
        to_delete = sorted([i for i, r in enumerate(records, start=2) if int(r["ID"]) in ids], reverse=True)
        if to_delete:
            # Group contiguous rows for efficiency if needed, but for now simple:
            for row_idx in to_delete:
                self.sheet.delete_rows(row_idx)
            self.reindex()

    def reindex(self):
        records = self.get_all()
        if not records:
            return
        
        # Sort: pending first, then by date
        records.sort(key=lambda x: (x["Status"] == "done", x["Created"]))
        
        new_data = []
        for i, r in enumerate(records, start=1):
            new_data.append([i, r["Task"], r["Status"], r["Created"]])
        
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
@click.pass_obj
def list_todos(store, show_all):
    """Show todo items."""
    rows = store.get_all()
    if not show_all:
        rows = [r for r in rows if r["Status"] != "done"]

    if not rows:
        click.echo("No pending todos." if not show_all else "No todos found.")
        return

    table = [
        [
            r["ID"],
            r["Task"],
            click.style("done", fg="green") if r["Status"] == "done" else click.style("pending", fg="yellow"),
            r["Created"],
        ]
        for r in rows
    ]
    click.echo(tabulate(table, headers=store.HEADERS, tablefmt="rounded_outline"))

@cli.command("add")
@click.argument("task")
@click.pass_obj
def add_todo(store, task):
    """Add a new todo item."""
    store.add(task)
    click.echo(f"Added: {task}")

@cli.command("done")
@click.argument("ids", type=int, nargs=-1)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def mark_done(store, ids, yes):
    """Mark todo items as complete."""
    if not ids: return
    records = [r for r in store.get_all() if int(r["ID"]) in ids and r["Status"] != "done"]
    if not records:
        click.echo("No pending todos found for given IDs.")
        return

    if not yes:
        click.confirm(f"Mark tasks {', '.join(str(r['ID']) for r in records)} as done?", abort=True)
    
    store.mark_done(ids)
    for r in records:
        click.echo(f"Marked #{r['ID']} as done: {r['Task']}")

@cli.command("delete")
@click.argument("ids", type=int, nargs=-1)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_obj
def delete_todo(store, ids, yes):
    """Delete todo items."""
    if not ids: return
    records = [r for r in store.get_all() if int(r["ID"]) in ids]
    if not records:
        click.echo("No todos found for given IDs.")
        return

    if not yes:
        click.confirm(f"Delete tasks {', '.join(str(r['ID']) for r in records)}?", abort=True)
    
    store.delete(ids)
    for r in records:
        click.echo(f"Deleted: {r['Task']}")

@cli.command("url")
@click.pass_obj
def show_url(store):
    """Show the URL of the current Google Spreadsheet."""
    click.echo(store.sheet.spreadsheet.url)

@cli.command("interactive")
@click.pass_context
def interactive(ctx):
    """Start an interactive session to manage tasks."""
    store = ctx.obj
    click.echo(click.style("Welcome to the Interactive Todo Manager!", fg="cyan", bold=True))
    click.echo("Commands: list [--all], add <task>, done [ids...], delete [ids...], url, exit")
    click.echo("Type 'c' or 'cancel' to abort any prompt.")
    
    while True:
        try:
            user_input = click.prompt("> ", default="", show_default=False).strip()
        except (click.Abort, EOFError):
            click.echo("\nGoodbye!")
            break
            
        if not user_input: continue
        parts = user_input.split(maxsplit=1)
        cmd, args = parts[0].lower(), parts[1] if len(parts) > 1 else ""

        if cmd in ["exit", "quit"]:
            click.echo("Goodbye!")
            break
        elif cmd == "list":
            ctx.invoke(list_todos, show_all=("--all" in args))
        elif cmd == "url":
            ctx.invoke(show_url)
        elif cmd == "add":
            task = args or click.prompt("Enter task (or 'c')", default="", show_default=False)
            if task and task.lower() not in ["c", "cancel"]:
                ctx.invoke(add_todo, task=task)
        elif cmd in ["done", "delete"]:
            ids = [int(x) for x in args.split() if x.isdigit()]
            if not ids:
                ctx.invoke(list_todos, show_all=False)
                prompt_msg = f"Enter IDs to {cmd} (or 'c')"
                ids_input = click.prompt(prompt_msg, default="", show_default=False)
                if not ids_input or ids_input.lower() in ["c", "cancel"]:
                    continue
                ids = [int(x) for x in ids_input.split() if x.isdigit()]
            
            if ids:
                try:
                    if cmd == "done": ctx.invoke(mark_done, ids=ids, yes=False)
                    else: ctx.invoke(delete_todo, ids=ids, yes=False)
                except (click.Abort, SystemExit): pass
        else:
            ctx.invoke(add_todo, task=user_input)

@cli.command("config")
@click.option("--spreadsheet-id", help="Set an existing spreadsheet ID to use.")
@click.pass_obj
def configure(store, spreadsheet_id):
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
