"""TodoItem data model. Powered by GEMINI."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TodoItem:
    id: int
    task: str
    status: str
    created: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["TodoItem"]:
        try:
            return cls(
                id=int(data["ID"]),
                task=str(data["Task"]),
                status=str(data["Status"]),
                created=str(data["Created"]),
                description=str(data.get("Description", "")),
            )
        except (ValueError, KeyError):
            return None

    def to_row(self) -> List[Any]:
        return [self.id, self.task, self.status, self.created, self.description]
