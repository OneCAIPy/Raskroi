from cutting_app.app.domain.cut_tree import CutDirection, CutNode, RectArea
from cutting_app.app.domain.cutting_result import ActualCut, CuttingResult, PlacedPart, SheetCutResult, UnplacedPart
from cutting_app.app.domain.result_issue import ResultIssue, ResultIssueLevel


def validate_cutting_result(
    result: CuttingResult,
    *,
    tolerance_mm: float = 0.001,
    area_tolerance_mm2: float = 0.01,
) -> list[ResultIssue]:
    issues: list[ResultIssue] = []

    for sheet in result.sheets:
        issues.extend(
            _validate_sheet_result(
                sheet=sheet,
                tolerance_mm=tolerance_mm,
                area_tolerance_mm2=area_tolerance_mm2,
            )
        )

    for unplaced_part in result.unplaced_parts:
        issue = _validate_unplaced_part(unplaced_part)
        if issue is not None:
            issues.append(issue)

    return issues


def _validate_sheet_result(
    sheet: SheetCutResult,
    tolerance_mm: float,
    area_tolerance_mm2: float,
) -> list[ResultIssue]:
    issues: list[ResultIssue] = []
    usable_area = sheet.root.area

    issues.extend(_validate_placed_parts_inside_usable_area(sheet, usable_area, tolerance_mm))
    issues.extend(_validate_placed_parts_do_not_overlap(sheet, tolerance_mm))
    issues.extend(_validate_actual_cuts_inside_usable_area(sheet, usable_area, tolerance_mm))
    issues.extend(_validate_cut_tree_nodes(sheet))
    issues.extend(_validate_area_balance(sheet, usable_area, area_tolerance_mm2))

    return issues


def _validate_placed_parts_inside_usable_area(
    sheet: SheetCutResult,
    usable_area: RectArea,
    tolerance_mm: float,
) -> list[ResultIssue]:
    issues: list[ResultIssue] = []

    for part in sheet.placed_parts:
        part_area = _part_to_area(part)
        if _contains_rect(usable_area, part_area, tolerance_mm):
            continue

        issues.append(
            ResultIssue(
                level=ResultIssueLevel.ERROR,
                code="PART_OUTSIDE_USABLE_AREA",
                message="Размещённая деталь выходит за рабочую область листа.",
                sheet_name=sheet.sheet_name,
                part_number=part.part_number,
                context={
                    "x_mm": part.x_mm,
                    "y_mm": part.y_mm,
                    "width_mm": part.width_mm,
                    "height_mm": part.height_mm,
                },
            )
        )

    return issues


def _validate_placed_parts_do_not_overlap(
    sheet: SheetCutResult,
    tolerance_mm: float,
) -> list[ResultIssue]:
    issues: list[ResultIssue] = []

    for first_index, first_part in enumerate(sheet.placed_parts):
        first_area = _part_to_area(first_part)
        for second_part in sheet.placed_parts[first_index + 1 :]:
            second_area = _part_to_area(second_part)
            if not _rects_overlap(first_area, second_area, tolerance_mm):
                continue

            issues.append(
                ResultIssue(
                    level=ResultIssueLevel.ERROR,
                    code="PART_OVERLAP",
                    message="Размещённые детали пересекаются.",
                    sheet_name=sheet.sheet_name,
                    part_number=first_part.part_number,
                    context={
                        "first_part_number": first_part.part_number,
                        "second_part_number": second_part.part_number,
                    },
                )
            )

    return issues


def _validate_actual_cuts_inside_usable_area(
    sheet: SheetCutResult,
    usable_area: RectArea,
    tolerance_mm: float,
) -> list[ResultIssue]:
    issues: list[ResultIssue] = []

    for cut_index, cut in enumerate(sheet.actual_cuts):
        if _contains_point(usable_area, cut.x1_mm, cut.y1_mm, tolerance_mm) and _contains_point(
            usable_area,
            cut.x2_mm,
            cut.y2_mm,
            tolerance_mm,
        ):
            continue

        issues.append(
            ResultIssue(
                level=ResultIssueLevel.ERROR,
                code="CUT_OUTSIDE_USABLE_AREA",
                message="Фактический рез выходит за рабочую область листа.",
                sheet_name=sheet.sheet_name,
                context={
                    "cut_index": cut_index,
                    "x1_mm": cut.x1_mm,
                    "y1_mm": cut.y1_mm,
                    "x2_mm": cut.x2_mm,
                    "y2_mm": cut.y2_mm,
                },
            )
        )

    return issues


def _validate_cut_tree_nodes(sheet: SheetCutResult) -> list[ResultIssue]:
    issues: list[ResultIssue] = []

    for node in _collect_nodes(sheet.root):
        if node.is_leaf:
            issues.extend(_validate_leaf_node(sheet, node))
            continue

        issues.extend(_validate_inner_node(sheet, node))

    return issues


def _validate_leaf_node(sheet: SheetCutResult, node: CutNode) -> list[ResultIssue]:
    if node.part_number is not None and node.is_waste:
        return [
            ResultIssue(
                level=ResultIssueLevel.ERROR,
                code="PART_LEAF_MARKED_AS_WASTE",
                message="Лист дерева с деталью ошибочно помечен как отход.",
                sheet_name=sheet.sheet_name,
                part_number=node.part_number,
            )
        ]

    if node.part_number is None and not node.is_waste:
        return [
            ResultIssue(
                level=ResultIssueLevel.ERROR,
                code="WASTE_LEAF_NOT_MARKED",
                message="Свободный лист дерева не помечен как отход.",
                sheet_name=sheet.sheet_name,
            )
        ]

    return []


def _validate_inner_node(sheet: SheetCutResult, node: CutNode) -> list[ResultIssue]:
    issues: list[ResultIssue] = []

    if node.is_waste:
        issues.append(
            ResultIssue(
                level=ResultIssueLevel.ERROR,
                code="INNER_NODE_MARKED_AS_WASTE",
                message="Внутренний узел дерева резов не должен быть помечен как отход.",
                sheet_name=sheet.sheet_name,
            )
        )

    if node.cut is None or node.first is None or node.second is None:
        issues.append(
            ResultIssue(
                level=ResultIssueLevel.ERROR,
                code="BROKEN_CUT_NODE",
                message="Внутренний узел дерева резов должен иметь рез и две дочерние области.",
                sheet_name=sheet.sheet_name,
            )
        )

    return issues


def _validate_area_balance(
    sheet: SheetCutResult,
    usable_area: RectArea,
    area_tolerance_mm2: float,
) -> list[ResultIssue]:
    usable_area_mm2 = usable_area.width_mm * usable_area.height_mm
    placed_area_mm2 = sum(part.width_mm * part.height_mm for part in sheet.placed_parts)
    waste_area_mm2 = sum(area.width_mm * area.height_mm for area in sheet.waste_areas)
    kerf_area_mm2 = sum(_actual_cut_length(cut) * cut.kerf_width_mm for cut in sheet.actual_cuts)
    actual_area_mm2 = placed_area_mm2 + waste_area_mm2 + kerf_area_mm2
    difference_mm2 = actual_area_mm2 - usable_area_mm2

    if abs(difference_mm2) <= area_tolerance_mm2:
        return []

    return [
        ResultIssue(
            level=ResultIssueLevel.ERROR,
            code="AREA_BALANCE_MISMATCH",
            message="Площадь деталей, отходов и пропила не сходится с рабочей площадью листа.",
            sheet_name=sheet.sheet_name,
            context={
                "usable_area_mm2": usable_area_mm2,
                "actual_area_mm2": actual_area_mm2,
                "difference_mm2": difference_mm2,
            },
        )
    ]


def _validate_unplaced_part(unplaced_part: UnplacedPart) -> ResultIssue | None:
    if unplaced_part.reason_code and unplaced_part.reason:
        return None

    return ResultIssue(
        level=ResultIssueLevel.ERROR,
        code="UNPLACED_PART_WITHOUT_REASON",
        message="Неразмещённая деталь должна иметь код причины и понятное описание.",
        part_number=unplaced_part.part_number,
    )


def _collect_nodes(node: CutNode) -> list[CutNode]:
    nodes = [node]

    if node.first is not None:
        nodes.extend(_collect_nodes(node.first))

    if node.second is not None:
        nodes.extend(_collect_nodes(node.second))

    return nodes


def _part_to_area(part: PlacedPart) -> RectArea:
    return RectArea(
        x_mm=part.x_mm,
        y_mm=part.y_mm,
        width_mm=part.width_mm,
        height_mm=part.height_mm,
    )


def _contains_rect(bounds: RectArea, area: RectArea, tolerance_mm: float) -> bool:
    return (
        area.x_mm >= bounds.x_mm - tolerance_mm
        and area.y_mm >= bounds.y_mm - tolerance_mm
        and area.right_mm <= bounds.right_mm + tolerance_mm
        and area.bottom_mm <= bounds.bottom_mm + tolerance_mm
    )


def _contains_point(bounds: RectArea, x_mm: float, y_mm: float, tolerance_mm: float) -> bool:
    return (
        x_mm >= bounds.x_mm - tolerance_mm
        and y_mm >= bounds.y_mm - tolerance_mm
        and x_mm <= bounds.right_mm + tolerance_mm
        and y_mm <= bounds.bottom_mm + tolerance_mm
    )


def _rects_overlap(first: RectArea, second: RectArea, tolerance_mm: float) -> bool:
    overlap_width = min(first.right_mm, second.right_mm) - max(first.x_mm, second.x_mm)
    overlap_height = min(first.bottom_mm, second.bottom_mm) - max(first.y_mm, second.y_mm)
    return overlap_width > tolerance_mm and overlap_height > tolerance_mm


def _actual_cut_length(cut: ActualCut) -> float:
    if cut.direction == CutDirection.VERTICAL:
        return cut.y2_mm - cut.y1_mm

    return cut.x2_mm - cut.x1_mm
