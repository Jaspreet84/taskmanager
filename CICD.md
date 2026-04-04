# CI/CD Strategy - `todo-cli`

This document outlines the Continuous Integration and Continuous Deployment (CI/CD) strategy for the `todo-cli` project. The goal is to ensure code quality, maintain high test coverage, and automate the distribution of both the Python package and the Gemini CLI skill.

## 1. Objectives
*   **Quality Assurance**: Automated linting and type checking to maintain PEP 8 standards.
*   **Regression Testing**: Ensure all logic, performance, and resiliency tests pass on every change.
*   **Automated Packaging**: Streamline the creation of Python wheels and `.skill` files.
*   **Secure Credential Handling**: Prevent the accidental leakage of Google Cloud secrets.

## 2. Pipeline Architecture
We recommend using **GitHub Actions** (given the repository's current hosting) to execute the following pipeline.

### Stage 1: Validation (Lint & Type Check)
*   **Tooling**: `ruff` (for linting and formatting), `mypy` (for static type checking).
*   **Trigger**: Every push and Pull Request.
*   **Success Criteria**: Zero linting errors and no type mismatches in `cli.py`, `storage.py`, `models.py`, and `config.py`.

### Stage 2: Automated Testing
*   **Tooling**: `pytest`.
*   **Environment**: Matrix testing on Python 3.9, 3.10, and 3.11+.
*   **Strategy**: Execute `test_todo.py`. Since tests utilize extensive mocking of the Google Sheets API, they can run in a virtualized environment without requiring live API access or secrets.
*   **Coverage Reporting**: Use `pytest-cov` to track coverage, aiming for >90%.

### Stage 3: Build & Package
*   **Python Build**: Generate source distributions and wheels using `build`.
*   **Skill Build**: Automate the packaging of the `todo-cli/` directory into a `.skill` file.
*   **Artifacts**: Store built packages as GitHub Action artifacts for manual verification before release.

### Stage 4: Release (Deployment)
*   **Trigger**: Creation of a new Git tag (e.g., `v1.0.0`).
*   **Python**: Automatically publish the verified wheel to PyPI.
*   **Skill**: Attach the latest `todo-cli.skill` to the GitHub Release notes for direct user download.

## 3. Secrets & Security
*   **Credential Protection**: The `credentials.json` and `token.json` files are explicitly ignored by `.gitignore`.
*   **CI Environment**: For integration tests that require a live Google Sheet, a Service Account JSON should be stored in **GitHub Secrets** and injected as an environment variable (`GOOGLE_CREDENTIALS_JSON`) during the run.

## 4. Automation Snippet (GitHub Actions)
```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt pytest pytest-mock
      - name: Run Tests
        run: pytest test_todo.py
```

---
*Powered by GEMINI*
