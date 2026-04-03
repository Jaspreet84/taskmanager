"""CLI command definitions and interactive loop logic. Powered by GEMINI."""
import shlex
import sys
from datetime import datetime
from typing import List

import click
from tabulate import tabulate

from storage import TodoStore
from config import Config

# ── CLI Commands ──────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Todo list manager backed by Google Sheets."""
    if ctx.obj is None:
        ctx.obj = TodoStore(Config())
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_todos)

@cli.command("list")
@click.option("-a", "show_all", is_flag=True, help="Include completed items.")
@click.option("--completed", "-d", "show_completed", is_flag=True, help="Show only completed items.")
@click.pass_obj
def list_todos(store: TodoStore, show_all: bool, show_completed: bool):
    """Show todo items."""
    all_items = store.get_all()
    pending_count = sum(1 for i in all_items if i.status != "done")
    done_count = sum(1 for i in all_items if i.status == "done")

    if show_completed:
        display_items = [i for i in all_items if i.status == "done"]
    elif not show_all:
        display_items = [i for i in all_items if i.status != "done"]
    else:
        display_items = all_items

    if display_items:
        now = datetime.now()
        table = []
        for i in display_items:
            # Parse created date
            try:
                created_dt = datetime.strptime(i.created, "%Y-%m-%d %H:%M")
                delta = now - created_dt
                days = delta.days
                
                if days < 3:
                    age_str = click.style(f"{days}d", fg="green")
                elif days < 7:
                    age_str = click.style(f"{days}d", fg="yellow")
                else:
                    age_str = click.style(f"{days}d", fg="red")
            except ValueError:
                age_str = "-"

            table.append([
                i.id,
                i.task,
                click.style("done", fg="green") if i.status == "done" else click.style("pending", fg="yellow"),
                age_str,
                i.created,
            ])
        
        headers = ["ID", "Task", "Status", "Age", "Created"]
        click.echo(tabulate(table, headers=headers, tablefmt="rounded_outline"))
    else:
        if show_completed:
            click.echo("No completed todos found.")
        elif not show_all:
            click.echo("No pending todos.")
        else:
            click.echo("No todos found.")

    # Show summary
    summary = (
        f"Summary: {click.style(str(pending_count), fg='yellow')} pending, "
        f"{click.style(str(done_count), fg='green')} completed "
        f"({len(all_items)} total)"
    )
    click.echo(summary)

@cli.command("add")
@click.argument("task")
@click.option("--desc", "-m", help="Detailed task description (optional).")
@click.pass_obj
def add_todo(store: TodoStore, task: str, desc: str):
    """Add a new todo item with an optional description."""
    store.add(task, desc or "")
    click.echo(f"Added: {task}")

@cli.command("show")
@click.argument("id", type=int)
@click.pass_obj
def show_todo(store: TodoStore, id: int):
    """Show detailed information for a task."""
    items = [i for i in store.get_all() if i.id == id]
    if not items:
        click.echo(f"No task found with ID {id}")
        return
    
    item = items[0]
    click.echo(click.style(f"\nTask #{item.id}: {item.task}", bold=True))
    click.echo(f"Status:      {click.style(item.status, fg='green' if item.status == 'done' else 'yellow')}")
    click.echo(f"Created:     {item.created}")
    click.echo(f"Description: {item.description or '(no description)'}\n")

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
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt (deletes everything).")
@click.pass_obj
def delete_todo(store: TodoStore, ids: List[int], yes: bool):
    """Delete todo items."""
    if not ids: return
    all_items = store.get_all()
    items_to_delete = [i for i in all_items if i.id in ids]
    
    if not items_to_delete:
        click.echo("No todos found for given IDs.")
        return

    ids_to_actually_delete = list(ids)

    if not yes:
        pending_items = [i for i in items_to_delete if i.status != "done"]
        done_items = [i for i in items_to_delete if i.status == "done"]
        
        if done_items:
            if pending_items:
                click.echo(click.style(f"Warning: {len(done_items)} of the selected tasks are already completed.", fg="yellow"))
                choice = click.prompt(
                    "Do you want to delete [A]ll selected, [S]kip completed and only delete pending, or [C]ancel?",
                    type=click.Choice(['a', 's', 'c'], case_sensitive=False),
                    default='c'
                )
                if choice.lower() == 'c':
                    click.echo("Aborted.")
                    return
                elif choice.lower() == 's':
                    ids_to_actually_delete = [i.id for i in pending_items]
                    items_to_delete = pending_items
            else:
                # Only completed items selected
                click.confirm(click.style("All selected tasks are already completed. Delete them anyway?", fg="yellow"), abort=True)
        else:
            # Only pending items
            click.confirm(f"Delete {len(items_to_delete)} pending tasks?", abort=True)
    
    if not ids_to_actually_delete:
        click.echo("No tasks to delete.")
        return

    store.delete(ids_to_actually_delete)
    for i in items_to_delete:
        click.echo(f"Deleted: {i.task}")

@cli.command("url")
@click.pass_obj
def show_url(store: TodoStore):
    """Show the URL of the current Google Spreadsheet."""
    click.echo(store.sheet.spreadsheet.url)

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

@cli.command("interactive")
@click.pass_context
def interactive(ctx: click.Context):
    """Start an interactive session to manage tasks."""
    store: TodoStore = ctx.obj
    
    def print_help():
        click.echo(click.style("\nAvailable Commands:", bold=True))
        click.echo("  l [-d|-a]        - Show tasks (default: pending, -d: done, -a: all)")
        click.echo("  show <id>        - Show task details including description")
        click.echo("  add <task> [-m <desc>] - Add a new task with optional description")
        click.echo("  done [ids...]    - Mark tasks as complete")
        click.echo("  delete [ids...]  - Remove tasks")
        click.echo("  url              - Show spreadsheet link")
        click.echo("  help             - Show this help message")
        click.echo("  exit/quit        - Close the session")
        click.echo("  Type 'c' or 'cancel' to abort any prompt.")

    click.echo(click.style("Welcome to the Interactive Todo Manager!", fg="cyan", bold=True))
    ctx.invoke(list_todos)
    click.echo(" (press 'h' for help)")
    
    while True:
        try:
            # Use manual loop to build the line to support "instant h" 
            # and allow backspacing over the first character.
            click.echo("> ", nl=False)
            
            if not sys.stdin.isatty():
                line = sys.stdin.readline().strip()
                if not line: break
                click.echo(line)
            else:
                line = ""
                while True:
                    c = click.getchar()
                    
                    # Handle Enter
                    if c in ('\r', '\n'):
                        click.echo("")
                        break
                    
                    # Handle Backspace / Delete
                    if c in ('\x7f', '\x08'):
                        if line:
                            line = line[:-1]
                            # Erase char: backspace, space, backspace
                            click.echo('\b \b', nl=False)
                        continue
                    
                    # Handle Ctrl+C (Interrupt) or Ctrl+D (EOF)
                    if c == '\x03' or c == '\x04':
                        click.echo("") # New line before goodbye
                        raise EOFError
                    
                    # "Instant h" - only if it's the first character
                    if not line and c.lower() == 'h':
                        click.echo("h")
                        print_help()
                        line = None
                        break
                    
                    # Ignore other non-printable or escape characters for simplicity
                    if ord(c) < 32 and c not in ('\r', '\n', '\b'):
                        continue
                        
                    line += c
                    click.echo(c, nl=False)
                
                if line is None: continue
                line = line.strip()

        except (click.Abort, EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye!")
            break
            
        if not line: continue
        
        try:
            parts = shlex.split(line)
        except ValueError as e:
            click.echo(f"\nError parsing command: {e}")
            continue

        if not parts: continue
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ["exit", "quit"]:
            click.echo("Goodbye!")
            break
        elif cmd in ["help", "h"]:
            print_help()
        elif cmd in ["list", "l"] or cmd.startswith("l-"):
            if cmd.startswith("l-"):
                # Handle cases like "l-a" where no space was provided
                actual_args = [cmd[1:]] + args
            else:
                actual_args = args
            
            show_all = "-a" in actual_args or "--all" in actual_args
            show_completed = "-d" in actual_args or "--completed" in actual_args
            ctx.invoke(list_todos, show_all=show_all, show_completed=show_completed)
        elif cmd == "show":
            if args:
                try:
                    ctx.invoke(show_todo, id=int(args[0]))
                except ValueError:
                    click.echo("Invalid task ID.")
            else:
                try:
                    id_input = click.prompt("Enter task ID", type=int)
                    ctx.invoke(show_todo, id=id_input)
                except (click.Abort, click.BadParameter): pass
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
