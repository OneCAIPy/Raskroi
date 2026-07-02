from cutting_app.app.domain.cut_tree import CutDirection, CutNode, RectArea
from cutting_app.app.domain.cutting_result import ActualCut, CuttingResult, PlacedPart, SheetCutResult, UnplacedPart
from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.domain.result_issue import ResultIssue, ResultIssueLevel
from cutting_app.app.exporters.svg_exporter import export_cutting_result_to_svg


def test_svg_exporter_draws_sheet_parts_waste_cuts_and_rotated_edges() -> None:
	result = CuttingResult(
		sheets=[
			SheetCutResult(
				sheet_name="S1",
				sheet_width_mm=600,
				sheet_height_mm=400,
				root=CutNode(area=RectArea(x_mm=10, y_mm=20, width_mm=560, height_mm=340)),
				placed_parts=[
					PlacedPart(
						part_number="A1",
						source_part_number="A",
						part_name="Полка",
						sheet_name="S1",
						x_mm=10,
						y_mm=20,
						width_mm=100,
						height_mm=80,
						rotation=Rotation.DEG_90,
						edges=EdgeSet(
							L1=EdgeSpec(thickness_mm=1),
							W1=EdgeSpec(thickness_mm=2),
						),
					),
				],
				waste_areas=[RectArea(x_mm=113, y_mm=20, width_mm=457, height_mm=340)],
				actual_cuts=[
					ActualCut(
						direction=CutDirection.VERTICAL,
						x1_mm=110,
						y1_mm=20,
						x2_mm=110,
						y2_mm=360,
						kerf_width_mm=3,
					),
				],
			),
		],
	)

	svg = export_cutting_result_to_svg(result)

	assert svg.startswith('<?xml version="1.0"')
	assert 'data-kind="sheet-outline"' in svg
	assert 'data-kind="usable-area"' in svg
	assert 'data-kind="placed-part"' in svg
	assert 'data-kind="waste-area"' in svg
	assert 'data-kind="actual-cut"' in svg
	assert '>A1<' in svg
	assert '100×80' in svg
	assert 'data-logical-side="L1"' in svg
	assert 'data-visual-side="right"' in svg
	assert 'data-logical-side="W1"' in svg
	assert 'data-visual-side="top"' in svg


def test_svg_exporter_draws_validator_issues_and_unplaced_parts() -> None:
	result = CuttingResult(
		unplaced_parts=[
			UnplacedPart(
				part_number="B1",
				source_part_number="B",
				part_name="Большая боковина",
				reason_code="DETAIL_DOES_NOT_FIT",
				reason="Деталь не помещается.",
			),
		],
	)
	issues = [
		ResultIssue(
			level=ResultIssueLevel.WARNING,
			code="TEST_WARNING",
			message="Проверочное предупреждение.",
		),
	]

	svg = export_cutting_result_to_svg(result, issues=issues)

	assert 'data-kind="result-issue"' in svg
	assert 'TEST_WARNING' in svg
	assert 'DETAIL_DOES_NOT_FIT' in svg
	assert 'B1' in svg
