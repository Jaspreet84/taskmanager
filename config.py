"""Configuration management and environment overrides. Powered by GEMINI."""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    def __init__(self, config_dir: Optional[os.PathLike[str]] = None):
        # Allow overriding config directory via environment variable or parameter
        env_dir = os.environ.get("TODO_CONFIG_DIR")
        if env_dir:
            self.dir = Path(env_dir)
        elif config_dir:
            self.dir = Path(config_dir)
        else:
            self.dir = Path.home() / ".config" / "todo-cli"

        self.token_file = self.dir / "token.json"
        self.creds_file = self.dir / "credentials.json"
        self.config_file = self.dir / "config.json"
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]
        self.ensure_dir()

    def ensure_dir(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                content = self.config_file.read_text()
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                return {}
        return {}

    def save(self, data: Dict[str, Any]) -> None:
        self.config_file.write_text(json.dumps(data, indent=2))

    def get_spreadsheet_id(self) -> Optional[str]:
        val = self.load().get("spreadsheet_id")
        return str(val) if val else None

    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        data = self.load()
        data["spreadsheet_id"] = spreadsheet_id
        self.save(data)
