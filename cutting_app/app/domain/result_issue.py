from dataclasses import dataclass, field
from enum import Enum


class ResultIssueLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ResultIssue:
    level: ResultIssueLevel
    code: str
    message: str
    sheet_name: str | None = None
    part_number: str | None = None
    context: dict[str, str | int | float] = field(default_factory=dict)
