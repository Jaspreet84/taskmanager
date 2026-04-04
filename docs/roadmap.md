# todo-cli Roadmap

This document outlines the planned improvements and future vision for the `todo-cli` manager.

## Phase 1: Interactive UX & Discoverability
*   **Command Auto-completion**: Integrate `prompt_toolkit` to allow for Tab-completion of commands and Task IDs.
*   **Command History**: Support standard arrow-key history in the interactive loop.
*   **Rich Visuals**: Replace basic `tabulate` with the `rich` library for better-looking tables, panels, and progress indicators.

## Phase 2: Core Task Logic
*   **Prioritization**: Add task priority levels (High/Medium/Low).
*   **Due Dates**: Implement urgency tracking and "Sort by Urgency" views.
*   **Search & Filtering**: Add a `search <keyword>` command to find specific tasks across all statuses.
*   **Tags/Categories**: Support for grouping tasks (e.g., `#work`, `#personal`).

## Phase 3: Reliability & Performance
*   **Offline Mode**: Implement a local cache (SQLite or JSON) that syncs with Google Sheets in the background to ensure "instant" performance.
*   **Undo Functionality**: Add a local transaction log to allow `undo` for the last delete or status change.
*   **Automated Setup**: Create a `todo setup` command to guide users through the initial Google Cloud credential configuration.

## Phase 4: Data & Portability
*   **Export/Import**: Add commands to export to CSV or import from JSON.
*   **Multi-Sheet Support**: Allow switching between different todo lists/sheets within the same account.

---
*Powered by GEMINI*
