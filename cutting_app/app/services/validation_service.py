from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.validation import ValidationIssue
from cutting_app.app.services.size_calculator import calculate_part_sizes
from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.sheet import SheetInput


def validate_part_input(part: PartInput) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if part.l_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_L_SIZE",
                message="Размер L должен быть больше 0.",
            )
        )

    if part.w_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_W_SIZE",
                message="Размер W должен быть больше 0.",
            )
        )

    if part.quantity <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_QUANTITY",
                message="Количество деталей должно быть больше 0.",
            )
        )

    if issues:
        return issues

    sizes = calculate_part_sizes(part)

    if sizes.no_edge_l_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_NO_EDGE_L_SIZE",
                message="Размер L без кромки должен быть больше 0.",
            )
        )

    if sizes.no_edge_w_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_NO_EDGE_W_SIZE",
                message="Размер W без кромки должен быть больше 0.",
            )
        )

    if sizes.cutting_l_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_CUTTING_L_SIZE",
                message="Распиловочный размер L должен быть больше 0.",
            )
        )

    if sizes.cutting_w_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_CUTTING_W_SIZE",
                message="Распиловочный размер W должен быть больше 0.",
            )
        )

    return issues

def validate_sheet_input(sheet: SheetInput) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if sheet.width_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_SHEET_WIDTH",
                message="Ширина листа должна быть больше 0.",
            )
        )

    if sheet.height_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_SHEET_HEIGHT",
                message="Высота листа должна быть больше 0.",
            )
        )

    if sheet.quantity <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_SHEET_QUANTITY",
                message="Количество листов должно быть больше 0.",
            )
        )

    usable_width = sheet.width_mm - sheet.margins.left_mm - sheet.margins.right_mm
    usable_height = sheet.height_mm - sheet.margins.top_mm - sheet.margins.bottom_mm

    if usable_width <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_USABLE_SHEET_WIDTH",
                message="Полезная ширина листа должна быть больше 0.",
            )
        )

    if usable_height <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_USABLE_SHEET_HEIGHT",
                message="Полезная высота листа должна быть больше 0.",
            )
        )

    return issues


def validate_cut_settings(settings: CutSettings) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if settings.kerf_width_mm <= 0:
        issues.append(
            ValidationIssue(
                code="INVALID_KERF_WIDTH",
                message="Ширина пилы должна быть больше 0.",
            )
        )

    return issues