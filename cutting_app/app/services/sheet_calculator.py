from dataclasses import dataclass

from cutting_app.app.domain.sheet import SheetInput


@dataclass(frozen=True)
class UsableSheetArea:
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


def calculate_usable_sheet_area(sheet: SheetInput) -> UsableSheetArea:
    return UsableSheetArea(
        x_mm=sheet.margins.left_mm,
        y_mm=sheet.margins.top_mm,
        width_mm=sheet.width_mm - sheet.margins.left_mm - sheet.margins.right_mm,
        height_mm=sheet.height_mm - sheet.margins.top_mm - sheet.margins.bottom_mm,
    )