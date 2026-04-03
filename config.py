"""Configuration management and environment overrides. Powered by GEMINI."""
import json
import os
from pathlib import Path
from typing import Dict, Optional

class Config:
    def __init__(self, config_dir: Optional[Path] = None):
        # Allow overriding config directory via environment variable or parameter
        env_dir = os.environ.get("TODO_CONFIG_DIR")
        if env_dir:
            self.dir = Path(env_dir)
        elif config_dir:
            self.dir = config_dir
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

    def ensure_dir(self):
        self.dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict:
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def save(self, data: Dict):
        self.config_file.write_text(json.dumps(data, indent=2))

    def get_spreadsheet_id(self) -> Optional[str]:
        return self.load().get("spreadsheet_id")

    def set_spreadsheet_id(self, spreadsheet_id: str):
        data = self.load()
        data["spreadsheet_id"] = spreadsheet_id
        self.save(data)
