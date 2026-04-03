from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class TodoItem:
    id: int
    task: str
    status: str
    created: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> Optional["TodoItem"]:
        try:
            return cls(
                id=int(data["ID"]),
                task=data["Task"],
                status=data["Status"],
                created=data["Created"],
                description=data.get("Description", "")
            )
        except (ValueError, KeyError):
            return None

    def to_row(self) -> List:
        return [self.id, self.task, self.status, self.created, self.description]
