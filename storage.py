"""Google Sheets API interaction and synchronization. Powered by GEMINI."""
import sys
from datetime import datetime
from typing import List, Optional

import click
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError

from models import TodoItem
from config import Config

class TodoStore:
    SHEET_NAME = "Todos"
    HEADERS = ["ID", "Task", "Status", "Created", "Description"]

    def __init__(self, config: Config):
        self.config = config
        self._sheet = None

    def get_credentials(self):
        if not self.config.creds_file.exists():
            click.echo(f"Error: credentials.json not found at {self.config.creds_file}", err=True)
            sys.exit(1)

        creds = None
        if self.config.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.config.token_file), self.config.scopes)
            except Exception:
                pass

        if not creds or not creds.valid:
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.config.creds_file), self.config.scopes)
                    creds = flow.run_local_server(port=0)
                self.config.token_file.write_text(creds.to_json())
            except (GoogleAuthError, Exception) as e:
                click.echo(f"Authentication error: {e}", err=True)
                sys.exit(1)
        return creds

    @property
    def sheet(self):
        if self._sheet is None:
            try:
                creds = self.get_credentials()
                gc = gspread.authorize(creds)
                spreadsheet_id = self.config.get_spreadsheet_id()
                
                spreadsheet = None
                if spreadsheet_id:
                    try:
                        spreadsheet = gc.open_by_key(spreadsheet_id)
                    except gspread.SpreadsheetNotFound:
                        click.echo(f"Warning: Spreadsheet ID {spreadsheet_id} not found. Creating new one.")
                        pass

                if spreadsheet is None:
                    spreadsheet = gc.create("Todo List")
                    self.config.set_spreadsheet_id(spreadsheet.id)
                    click.echo(f"Created new spreadsheet: {spreadsheet.url}")

                try:
                    self._sheet = spreadsheet.worksheet(self.SHEET_NAME)
                except gspread.WorksheetNotFound:
                    self._sheet = spreadsheet.add_worksheet(title=self.SHEET_NAME, rows=1000, cols=5)
                    self._sheet.append_row(self.HEADERS)

                # Ensure headers
                first_row = self._sheet.row_values(1)
                if not first_row or first_row[:5] != self.HEADERS:
                    self._sheet.insert_row(self.HEADERS, 1)
            except gspread.GSpreadException as e:
                click.echo(f"Google Sheets API error: {e}", err=True)
                sys.exit(1)
            except Exception as e:
                click.echo(f"Unexpected error: {e}", err=True)
                sys.exit(1)
        return self._sheet

    def get_all(self) -> List[TodoItem]:
        try:
            records = self.sheet.get_all_records()
            items = [TodoItem.from_dict(r) for r in records]
            return [i for i in items if i is not None]
        except Exception as e:
            click.echo(f"Error fetching todos: {e}", err=True)
            return []

    def add(self, task: str, description: str = ""):
        items = self.get_all()
        created = datetime.now().strftime("%Y-%m-%d %H:%M")
        items.append(TodoItem(id=0, task=task, status="pending", created=created, description=description))
        self.sync(items)

    def mark_done(self, ids: List[int]):
        items = self.get_all()
        changed = False
        for item in items:
            if item.id in ids and item.status != "done":
                item.status = "done"
                changed = True
        
        if changed:
            self.sync(items)

    def delete(self, ids: List[int]):
        items = self.get_all()
        # Keep only items NOT in the ids list
        new_items = [i for i in items if i.id not in ids]
        if len(new_items) != len(items):
            self.sync(new_items)

    def sync(self, items: List[TodoItem]):
        """Sort, re-index, and sync the entire item list to the sheet."""
        # Sort: pending first, then by date
        items.sort(key=lambda x: (x.status == "done", x.created))
        
        # Prepare data with new IDs
        new_data = [self.HEADERS]
        for i, item in enumerate(items, start=1):
            item.id = i
            new_data.append(item.to_row())
        
        try:
            # More efficient update strategy: 
            # 1. Clear existing content to avoid leftovers (but more safely if possible)
            # 2. Update with new data
            # For small to medium lists, clear + update is okay if wrapped in try/except.
            # Using batch_update would be even better for very large sheets.
            
            # Get current sheet size
            current_rows = self.sheet.row_count
            
            # Clear current data (range A1:E)
            self.sheet.clear()
            
            # Update starting from A1
            end_row = len(new_data)
            self.sheet.update(range_name=f"A1:E{end_row}", values=new_data)
            
        except Exception as e:
            click.echo(f"Error syncing to Google Sheets: {e}", err=True)
