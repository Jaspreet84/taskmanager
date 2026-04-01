#!/usr/bin/env python3
"""CLI todo list manager backed by Google Sheets."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import click
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from tabulate import tabulate

CONFIG_DIR = Path.home() / ".config" / "todo-cli"
TOKEN_FILE = CONFIG_DIR / "token.json"
CREDS_FILE = CONFIG_DIR / "credentials.json"
CONFIG_FILE = CONFIG_DIR / "config.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SHEET_NAME = "Todos"
HEADERS = ["ID", "Task", "Status", "Created"]


def get_credentials():
    """Get or refresh Google OAuth2 credentials."""
    if not CREDS_FILE.exists():
        click.echo(
            f"Error: credentials.json not found at {CREDS_FILE}\n"
            "See README for setup instructions.",
            err=True,
        )
        sys.exit(1)

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())

    return creds


def get_sheet():
    """Return the Todos worksheet, creating it if needed."""
    creds = get_credentials()
    config = load_config()
    gc = gspread.authorize(creds)

    spreadsheet_id = config.get("spreadsheet_id")
    if spreadsheet_id:
        try:
            spreadsheet = gc.open_by_key(spreadsheet_id)
        except gspread.SpreadsheetNotFound:
            spreadsheet = None
    else:
        spreadsheet = None

    if spreadsheet is None:
        spreadsheet = gc.create("Todo List")
        config["spreadsheet_id"] = spreadsheet.id
        save_config(config)
        click.echo(f"Created new spreadsheet: {spreadsheet.url}")

    try:
        sheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=4)
        sheet.append_row(HEADERS)

    # Ensure header row exists
    first_row = sheet.row_values(1)
    if first_row != HEADERS:
        sheet.insert_row(HEADERS, 1)

    return sheet


def load_config():
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_all_rows(sheet):
    """Return all data rows (excluding header) as list of dicts."""
    records = sheet.get_all_records()
    return records


def next_id(rows):
    if not rows:
        return 1
    return max(int(r["ID"]) for r in rows) + 1


# ── CLI ────────────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Todo list manager backed by Google Sheets."""


@cli.command("list")
@click.option("--all", "show_all", is_flag=True, help="Include completed items.")
def list_todos(show_all):
    """Show todo items."""
    sheet = get_sheet()
    rows = get_all_rows(sheet)

    if not show_all:
        rows = [r for r in rows if r["Status"] != "done"]

    if not rows:
        click.echo("No todos found." if show_all else "No pending todos. Use --all to see completed items.")
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
    click.echo(tabulate(table, headers=HEADERS, tablefmt="rounded_outline"))


@cli.command("add")
@click.argument("task")
def add_todo(task):
    """Add a new todo item."""
    sheet = get_sheet()
    rows = get_all_rows(sheet)
    new_id = next_id(rows)
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([new_id, task, "pending", created])
    click.echo(f"Added #{new_id}: {task}")


@cli.command("done")
@click.argument("id", type=int)
def mark_done(id):
    """Mark a todo item as complete."""
    sheet = get_sheet()
    rows = get_all_rows(sheet)

    for i, row in enumerate(rows, start=2):  # row 1 is header
        if int(row["ID"]) == id:
            if row["Status"] == "done":
                click.echo(f"#{id} is already marked done.")
                return
            sheet.update_cell(i, 3, "done")
            click.echo(f"Marked #{id} as done: {row['Task']}")
            return

    click.echo(f"Error: no todo with ID {id}.", err=True)
    sys.exit(1)


@cli.command("delete")
@click.argument("id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def delete_todo(id, yes):
    """Delete a todo item."""
    sheet = get_sheet()
    rows = get_all_rows(sheet)

    for i, row in enumerate(rows, start=2):
        if int(row["ID"]) == id:
            if not yes:
                click.confirm(f"Delete #{id}: '{row['Task']}'?", abort=True)
            sheet.delete_rows(i)
            click.echo(f"Deleted #{id}: {row['Task']}")
            return

    click.echo(f"Error: no todo with ID {id}.", err=True)
    sys.exit(1)


@cli.command("config")
@click.option("--spreadsheet-id", help="Set an existing spreadsheet ID to use.")
def configure(spreadsheet_id):
    """Show or update configuration."""
    config = load_config()
    if spreadsheet_id:
        config["spreadsheet_id"] = spreadsheet_id
        save_config(config)
        click.echo(f"Spreadsheet ID set to: {spreadsheet_id}")
    else:
        click.echo(f"Config file:    {CONFIG_FILE}")
        click.echo(f"Credentials:    {CREDS_FILE}")
        click.echo(f"Spreadsheet ID: {config.get('spreadsheet_id', '(not set — will be created on first use)')}")


if __name__ == "__main__":
    cli()
