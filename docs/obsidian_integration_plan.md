# Obsidian.md Integration Plan - `todo-cli`

This document outlines the strategy for integrating the Google Sheets-backed `todo-cli` with the Obsidian note-taking application.

## 1. Objectives
*   **Visibility**: View your Google Sheets todo list directly inside Obsidian.
*   **Synchronization**: Reflect task completion status between Obsidian and Google Sheets.
*   **Centralization**: Allow Obsidian's powerful "Tasks" and "Dataview" plugins to interact with `todo-cli` data.

## 2. Technical Strategy: The "Vault Sync"
The integration will act as a bridge that translates between the **Google Sheets API** and **Local Markdown Files** using standard Markdown checkbox syntax (`- [ ] task`).

### Core Workflow
1.  **Pull**: CLI reads tasks from Google Sheets and writes/updates a `Todos.md` file in the user's Obsidian Vault.
2.  **Push**: CLI reads the `Todos.md` file, detects changes in checkbox states, and updates Google Sheets accordingly.

## 3. Implementation Phases

### Phase 1: Configuration & Basic Export
*   **Config Update**: Add `obsidian_vault_path` and `obsidian_filename` to `config.py`.
*   **Formatters**: Create a Markdown formatter that converts `TodoItem` objects into `- [ ] task #id/1` strings.
*   **Sync Command**: Implement `todo obsidian sync` to perform a one-way export from Sheets to Markdown.

### Phase 2: Bidirectional Logic
*   **MD Parser**: Build a robust parser to read Markdown checkboxes and extract IDs and statuses.
*   **State Comparison**: Compare local MD state vs. remote Sheets state.
*   **Conflict Resolution**: Use the `created` or `modified` timestamps to decide which state wins in a conflict.

### Phase 3: Automation & UX
*   **Obsidian URI Support**: Generate `obsidian://` links in the CLI output to jump directly to specific notes.
*   **Background Sync**: (Optional) Add a lightweight watcher that periodically syncs the vault in the background.

## 4. Technical Architecture
A new module, `obsidian_bridge.py`, will be created to keep the core `storage.py` clean. 

```python
# Proposed logic snippet
def sync_to_markdown(tasks: List[TodoItem], path: Path):
    with open(path, "w") as f:
        f.write("# Google Sheets Todos\n\n")
        for task in tasks:
            status = "x" if task.status == "done" else " "
            f.write(f"- [{status}] {task.task} ^id-{task.id}\n")
```

---
*Powered by GEMINI*
