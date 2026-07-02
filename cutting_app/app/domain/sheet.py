from dataclasses import dataclass


@dataclass(frozen=True)
class SheetMargins:
    left_mm: float = 0.0
    top_mm: float = 0.0
    right_mm: float = 0.0
    bottom_mm: float = 0.0


@dataclass(frozen=True)
class SheetInput:
    name: str
    width_mm: float
    height_mm: float
    quantity: int = 1
    is_remnant: bool = False
    margins: SheetMargins = SheetMargins()