from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.validation import ValidationIssue
from cutting_app.app.services.size_calculator import calculate_part_sizes


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