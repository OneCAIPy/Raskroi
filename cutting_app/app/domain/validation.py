from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str