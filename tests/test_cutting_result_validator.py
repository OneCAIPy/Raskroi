from cutting_app.app.domain.cut_tree import CutDirection, CutNode, RectArea
from cutting_app.app.domain.cutting_result import ActualCut, CuttingResult, PlacedPart, SheetCutResult, UnplacedPart
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.services.cutting_result_validator import validate_cutting_result


def _placed_part(
    part_number: str,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
) -> PlacedPart:
    return PlacedPart(
        part_number=part_number,
        source_part_number=part_number,
        part_name=f"Деталь {part_number}",
        sheet_name="Лист",
        x_mm=x_mm,
        y_mm=y_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        rotation=Rotation.DEG_0,
    )


def _sheet_result(
    *,
    root: CutNode | None = None,
    placed_parts: list[PlacedPart] | None = None,
    waste_areas: list[RectArea] | None = None,
    actual_cuts: list[ActualCut] | None = None,
) -> SheetCutResult:
    return SheetCutResult(
        sheet_name="Лист",
        sheet_width_mm=1000,
        sheet_height_mm=1000,
        root=root or CutNode(
            area=RectArea(x_mm=0, y_mm=0, width_mm=1000, height_mm=1000),
            part_number="1",
        ),
        placed_parts=placed_parts or [],
        waste_areas=waste_areas or [],
        actual_cuts=actual_cuts or [],
    )


def _issue_codes(result: CuttingResult) -> set[str]:
    return {issue.code for issue in validate_cutting_result(result)}


def test_valid_cutting_result_has_no_issues():
    sheet = _sheet_result(
        placed_parts=[_placed_part("1", 0, 0, 1000, 1000)],
    )
    result = CuttingResult(sheets=[sheet])

    assert validate_cutting_result(result) == []


def test_validator_detects_part_outside_usable_area():
    sheet = _sheet_result(
        root=CutNode(
            area=RectArea(x_mm=10, y_mm=10, width_mm=100, height_mm=100),
            part_number="1",
        ),
        placed_parts=[_placed_part("1", 0, 10, 100, 100)],
    )
    result = CuttingResult(sheets=[sheet])

    assert "PART_OUTSIDE_USABLE_AREA" in _issue_codes(result)


def test_validator_detects_overlapping_parts():
    sheet = _sheet_result(
        placed_parts=[
            _placed_part("1", 0, 0, 600, 600),
            _placed_part("2", 500, 500, 300, 300),
        ],
        waste_areas=[RectArea(x_mm=0, y_mm=0, width_mm=0, height_mm=550000)],
    )
    result = CuttingResult(sheets=[sheet])

    assert "PART_OVERLAP" in _issue_codes(result)


def test_validator_detects_actual_cut_outside_usable_area():
    sheet = _sheet_result(
        placed_parts=[_placed_part("1", 0, 0, 1000, 1000)],
        actual_cuts=[
            ActualCut(
                direction=CutDirection.VERTICAL,
                x1_mm=-1,
                y1_mm=0,
                x2_mm=-1,
                y2_mm=1000,
                kerf_width_mm=4,
            )
        ],
    )
    result = CuttingResult(sheets=[sheet])

    assert "CUT_OUTSIDE_USABLE_AREA" in _issue_codes(result)


def test_validator_detects_wrong_waste_leaf_marking():
    sheet = _sheet_result(
        root=CutNode(area=RectArea(x_mm=0, y_mm=0, width_mm=1000, height_mm=1000)),
        waste_areas=[RectArea(x_mm=0, y_mm=0, width_mm=1000, height_mm=1000)],
    )
    result = CuttingResult(sheets=[sheet])

    assert "WASTE_LEAF_NOT_MARKED" in _issue_codes(result)


def test_validator_detects_area_balance_mismatch():
    sheet = _sheet_result(
        placed_parts=[_placed_part("1", 0, 0, 100, 100)],
    )
    result = CuttingResult(sheets=[sheet])


    assert "AREA_BALANCE_MISMATCH" in _issue_codes(result)


def test_validator_detects_unplaced_part_without_reason():
    result = CuttingResult(
        unplaced_parts=[
            UnplacedPart(
                part_number="1",
                source_part_number="1",
                part_name="Деталь 1",
                reason_code="",
                reason="",
            )
        ]
    )

    assert "UNPLACED_PART_WITHOUT_REASON" in _issue_codes(result)
