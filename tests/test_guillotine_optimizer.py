from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cut_tree import CutDirection
from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting
from cutting_app.app.services.cutting_result_validator import validate_cutting_result
from tests.basis_agt_3019_fixture import (
	build_basis_agt_3019_parts,
	build_basis_agt_3019_settings,
	build_basis_agt_3019_sheets,
)


def _part(
	number: str,
	l_mm: float,
	w_mm: float,
	quantity: int = 1,
	rotation_allowed: bool = True,
) -> PartInput:
	return PartInput(
		number=number,
		name=f"Деталь {number}",
		l_mm=l_mm,
		w_mm=w_mm,
		quantity=quantity,
		edges=EdgeSet(),
		rotation_allowed=rotation_allowed,
	)


def test_two_neighbor_parts_use_one_actual_kerf_between_them():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 400, 400, quantity=2)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000)],
		settings=CutSettings(kerf_width_mm=4),
	)

	sheet = result.sheets[0]
	first = sheet.placed_parts[0]
	second = sheet.placed_parts[1]

	assert first.x_mm == 0
	assert first.y_mm == 0
	assert second.x_mm == 0
	assert second.y_mm == 404
	assert second.y_mm - (first.y_mm + first.height_mm) == 4
	assert first.width_mm == 400
	assert second.width_mm == 400
	assert result.unplaced_parts == []


def test_remnant_sheet_is_used_before_standard_sheet():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 800, 500)],
		sheets=[
			SheetInput(name="Стандарт", width_mm=1500, height_mm=2800, is_remnant=False),
			SheetInput(name="Остаток", width_mm=1000, height_mm=2800, is_remnant=True),
		],
		settings=CutSettings(kerf_width_mm=4),
	)

	assert result.sheets[0].sheet_name == "Остаток"
	assert result.sheets[0].placed_parts[0].sheet_name == "Остаток"


def test_placement_respects_sheet_margins():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 100, 100)],
		sheets=[
			SheetInput(
				name="Лист",
				width_mm=1000,
				height_mm=1000,
				margins=SheetMargins(left_mm=10, top_mm=20, right_mm=10, bottom_mm=20),
			)
		],
		settings=CutSettings(kerf_width_mm=4),
	)

	placed = result.sheets[0].placed_parts[0]

	assert placed.x_mm == 10
	assert placed.y_mm == 20


def test_part_is_unplaced_when_it_does_not_fit_without_rotation():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 1200, 500, rotation_allowed=False)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=2800)],
		settings=CutSettings(kerf_width_mm=4),
	)

	assert result.sheets == []
	assert len(result.unplaced_parts) == 1
	assert result.unplaced_parts[0].reason_code == "DETAIL_DOES_NOT_FIT"


def test_part_is_placed_with_rotation_when_allowed():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 1200, 500, rotation_allowed=True)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=2800)],
		settings=CutSettings(kerf_width_mm=4),
	)

	placed = result.sheets[0].placed_parts[0]

	assert placed.rotation == Rotation.DEG_90
	assert placed.width_mm == 500
	assert placed.height_mm == 1200
	assert result.unplaced_parts == []


def test_finished_part_rotation_is_not_counted_as_strip_turn():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 120, 50, rotation_allowed=True)],
		sheets=[SheetInput(name="Лист", width_mm=50, height_mm=120)],
		settings=CutSettings(kerf_width_mm=4),
	)

	sheet = result.sheets[0]
	placed = sheet.placed_parts[0]
	plan = sheet.production_cut_plan

	assert placed.rotation == Rotation.DEG_90
	assert plan is not None
	assert plan.strip_turns == ()
	assert plan.metrics.strip_turn_count == 0


def test_finished_part_rotation_does_not_change_edge_consumption():
	part = PartInput(
		number="1",
		name="Поворачиваемая деталь",
		l_mm=120,
		w_mm=50,
		quantity=1,
		edges=EdgeSet(
			L1=EdgeSpec(thickness_mm=1, material_name="ABS 1 мм"),
			W1=EdgeSpec(thickness_mm=2, material_name="ABS 2 мм"),
		),
		rotation_allowed=True,
	)

	result = optimize_guillotine_cutting(
		parts=[part],
		sheets=[SheetInput(name="Лист", width_mm=50, height_mm=120)],
		settings=CutSettings(kerf_width_mm=4),
	)

	assert result.sheets[0].placed_parts[0].rotation == Rotation.DEG_90
	assert result.edge_consumption.segment_count == 2
	assert result.edge_consumption.base_length_mm == 170
	assert result.edge_consumption.total_length_mm == 170


def test_unplaced_part_does_not_add_production_edge_consumption():
	part = PartInput(
		number="1",
		name="Слишком большая деталь",
		l_mm=200,
		w_mm=200,
		quantity=1,
		edges=EdgeSet(L1=EdgeSpec(thickness_mm=1)),
		rotation_allowed=False,
	)

	result = optimize_guillotine_cutting(
		parts=[part],
		sheets=[SheetInput(name="Лист", width_mm=100, height_mm=100)],
		settings=CutSettings(kerf_width_mm=4),
	)

	assert result.metrics.unplaced_part_count == 1
	assert result.edge_consumption.segment_count == 0
	assert result.edge_consumption.total_length_mm == 0


def test_equal_split_score_keeps_vertical_first_for_determinism():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 400, 400)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000)],
		settings=CutSettings(kerf_width_mm=4),
	)

	root = result.sheets[0].root

	assert root.cut.direction == CutDirection.VERTICAL
	assert root.cut.position_mm == 400
	assert root.second.area.x_mm == 404


def test_horizontal_first_split_can_be_chosen_to_reduce_actual_kerf_loss():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 700, 200, rotation_allowed=False)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=800)],
		settings=CutSettings(kerf_width_mm=4),
	)

	root = result.sheets[0].root

	assert root.cut.direction == CutDirection.HORIZONTAL
	assert root.cut.position_mm == 200
	assert root.second.area.x_mm == 0
	assert root.second.area.y_mm == 204
	assert root.second.area.width_mm == 1000
	assert root.second.area.height_mm == 596
	assert root.first.cut.direction == CutDirection.VERTICAL
	assert root.first.second.area.x_mm == 704
	assert root.first.second.area.y_mm == 0
	assert root.first.second.area.width_mm == 296
	assert root.first.second.area.height_mm == 200


def test_candidate_selection_prefers_tighter_free_area_over_earlier_area():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 400, 400), _part("2", 300, 500)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000)],
		settings=CutSettings(kerf_width_mm=4),
	)

	placed_by_number = {part.source_part_number: part for part in result.sheets[0].placed_parts}
	second = placed_by_number["2"]

	assert second.x_mm == 0
	assert second.y_mm == 404
	assert second.width_mm == 300
	assert second.height_mm == 500
	assert result.unplaced_parts == []


def _collect_nodes(node):
	result = [node]
	if node.first is not None:
		result.extend(_collect_nodes(node.first))
	if node.second is not None:
		result.extend(_collect_nodes(node.second))
	return result


def test_cut_tree_marks_free_leaf_nodes_as_waste():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 400, 400), _part("2", 300, 500)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000)],
		settings=CutSettings(kerf_width_mm=4),
	)

	sheet = result.sheets[0]
	nodes = _collect_nodes(sheet.root)
	leaf_nodes = [node for node in nodes if node.is_leaf]
	part_leaf_nodes = [node for node in leaf_nodes if node.part_number is not None]
	waste_leaf_nodes = [node for node in leaf_nodes if node.part_number is None]

	assert len(part_leaf_nodes) == 2
	assert all(not node.is_waste for node in part_leaf_nodes)
	assert all(node.is_waste for node in waste_leaf_nodes)
	assert all(not node.is_waste for node in nodes if not node.is_leaf)
	assert set(node.area for node in waste_leaf_nodes) == set(sheet.waste_areas)


def test_exact_fit_leaf_is_part_not_waste():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 1000, 1000, rotation_allowed=False)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000)],
		settings=CutSettings(kerf_width_mm=4),
	)

	sheet = result.sheets[0]
	root = sheet.root

	assert root.is_leaf
	assert root.part_number == "1"
	assert root.is_waste is False
	assert sheet.waste_areas == []



def test_terminal_trim_cut_keeps_area_balance():
    result = optimize_guillotine_cutting(
        parts=[_part("1", 98, 100, rotation_allowed=False)],
        sheets=[SheetInput(name="Лист", width_mm=100, height_mm=100)],
        settings=CutSettings(kerf_width_mm=4),
    )

    assert result.unplaced_parts == []
    assert len(result.sheets) == 1

    sheet = result.sheets[0]

    assert sheet.metrics.placed_area_mm2 == 9800
    assert sheet.metrics.waste_area_mm2 == 0
    assert sheet.metrics.kerf_area_mm2 == 200
    assert sheet.metrics.placed_area_mm2 + sheet.metrics.waste_area_mm2 + sheet.metrics.kerf_area_mm2 == sheet.metrics.usable_area_mm2

    assert len(sheet.actual_cuts) == 1
    assert sheet.actual_cuts[0].direction == CutDirection.VERTICAL
    assert sheet.actual_cuts[0].kerf_width_mm == 2

    plan = sheet.production_cut_plan

    assert plan is not None
    assert plan.metrics.pass_count == 1
    assert plan.metrics.size_setting_count == 1
    assert plan.metrics.cut_length_mm == 100
    assert plan.metrics.nominal_cut_area_mm2 == 400
    assert plan.metrics.actual_removed_area_mm2 == 200

    issues = validate_cutting_result(result)

    assert [issue.code for issue in issues] == []


def test_regular_split_with_terminal_trim_keeps_area_balance():
    result = optimize_guillotine_cutting(
        parts=[_part("1", 50, 98, rotation_allowed=False)],
        sheets=[SheetInput(name="Лист", width_mm=100, height_mm=100)],
        settings=CutSettings(kerf_width_mm=4),
    )

    assert result.unplaced_parts == []
    assert len(result.sheets) == 1

    sheet = result.sheets[0]

    assert sheet.metrics.placed_area_mm2 == 4900
    assert sheet.metrics.waste_area_mm2 == 4600
    assert sheet.metrics.kerf_area_mm2 == 500
    assert sheet.metrics.placed_area_mm2 + sheet.metrics.waste_area_mm2 + sheet.metrics.kerf_area_mm2 == sheet.metrics.usable_area_mm2

    cut_kerf_widths = [cut.kerf_width_mm for cut in sheet.actual_cuts]
    assert cut_kerf_widths == [4, 2]

    issues = validate_cutting_result(result)

    assert [issue.code for issue in issues] == []
def test_sheet_result_contains_actual_cut_segments_from_tree():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 700, 200, rotation_allowed=False)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=800)],
		settings=CutSettings(kerf_width_mm=4),
	)

	actual_cuts = result.sheets[0].actual_cuts

	assert len(actual_cuts) == 2

	first_cut = actual_cuts[0]
	assert first_cut.direction == CutDirection.HORIZONTAL
	assert first_cut.x1_mm == 0
	assert first_cut.y1_mm == 200
	assert first_cut.x2_mm == 1000
	assert first_cut.y2_mm == 200
	assert first_cut.kerf_width_mm == 4

	second_cut = actual_cuts[1]
	assert second_cut.direction == CutDirection.VERTICAL
	assert second_cut.x1_mm == 700
	assert second_cut.y1_mm == 0
	assert second_cut.x2_mm == 700
	assert second_cut.y2_mm == 200
	assert second_cut.kerf_width_mm == 4


def test_sheet_result_contains_production_plan_from_full_sheet():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 700, 200, rotation_allowed=False)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=800)],
		settings=CutSettings(kerf_width_mm=4),
	)

	plan = result.sheets[0].production_cut_plan

	assert plan is not None
	assert plan.source_area.width_mm == 1000
	assert plan.source_area.height_mm == 800
	assert plan.metrics.cycle_count == 2
	assert plan.metrics.pass_count == 2
	assert plan.metrics.cut_length_mm == 1200
	assert plan.metrics.nominal_cut_area_mm2 == 4800
	assert plan.metrics.actual_removed_area_mm2 == 4800


def test_production_plan_includes_sheet_margin_trims():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 100, 100, rotation_allowed=False)],
		sheets=[
			SheetInput(
				name="Лист",
				width_mm=1000,
				height_mm=1000,
				margins=SheetMargins(
					left_mm=10,
					top_mm=20,
					right_mm=10,
					bottom_mm=20,
				),
			)
		],
		settings=CutSettings(kerf_width_mm=4),
	)

	plan = result.sheets[0].production_cut_plan

	assert plan is not None
	assert plan.metrics.cycle_count == 2
	assert plan.metrics.pass_count == 4
	assert plan.metrics.cut_length_mm == 2200
	assert plan.metrics.nominal_cut_area_mm2 == 8800


def test_exact_usable_part_uses_initial_cut_direction_from_settings():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 80, 60, rotation_allowed=False)],
		sheets=[
			SheetInput(
				name="Лист",
				width_mm=100,
				height_mm=100,
				margins=SheetMargins(
					left_mm=10,
					top_mm=20,
					right_mm=10,
					bottom_mm=20,
				),
			)
		],
		settings=CutSettings(
			kerf_width_mm=4,
			initial_cut_direction=CutDirection.HORIZONTAL,
		),
	)

	plan = result.sheets[0].production_cut_plan

	assert plan is not None
	assert [cycle.direction for cycle in plan.cycles] == [
		CutDirection.HORIZONTAL,
		CutDirection.VERTICAL,
	]
	assert plan.metrics.pass_count == 4


def test_exact_fit_sheet_result_has_no_actual_cuts():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 1000, 1000, rotation_allowed=False)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000)],
		settings=CutSettings(kerf_width_mm=4),
	)

	assert result.sheets[0].actual_cuts == []


def test_sheet_result_contains_area_metrics():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 700, 200, rotation_allowed=False)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=800)],
		settings=CutSettings(kerf_width_mm=4),
	)

	metrics = result.sheets[0].metrics

	assert metrics.sheet_area_mm2 == 800000
	assert metrics.usable_area_mm2 == 800000
	assert metrics.placed_area_mm2 == 140000
	assert metrics.waste_area_mm2 == 655200
	assert metrics.kerf_area_mm2 == 4800
	assert metrics.material_utilization_percent == 17.5
	assert metrics.working_area_efficiency_percent == 17.5
	assert metrics.placed_area_mm2 + metrics.waste_area_mm2 + metrics.kerf_area_mm2 == metrics.usable_area_mm2


def test_cutting_result_contains_total_metrics_and_unplaced_count():
	result = optimize_guillotine_cutting(
		parts=[
			_part("1", 700, 200, rotation_allowed=False),
			_part("2", 2000, 2000),
		],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=800)],
		settings=CutSettings(kerf_width_mm=4),
	)

	metrics = result.metrics

	assert metrics.sheet_count == 1
	assert metrics.placed_part_count == 1
	assert metrics.unplaced_part_count == 1
	assert metrics.sheet_area_mm2 == 800000
	assert metrics.usable_area_mm2 == 800000
	assert metrics.placed_area_mm2 == 140000
	assert metrics.waste_area_mm2 == 655200
	assert metrics.kerf_area_mm2 == 4800
	assert metrics.material_utilization_percent == 17.5
	assert metrics.working_area_efficiency_percent == 17.5


def test_material_utilization_uses_only_sheets_that_received_parts():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 100, 100)],
		sheets=[SheetInput(name="Лист", width_mm=1000, height_mm=1000, quantity=2)],
		settings=CutSettings(kerf_width_mm=4),
	)

	metrics = result.metrics

	assert metrics.sheet_count == 1
	assert metrics.sheet_area_mm2 == 1000000
	assert metrics.material_utilization_percent == 1


def test_sheet_metrics_use_usable_area_inside_margins():
	result = optimize_guillotine_cutting(
		parts=[_part("1", 100, 100)],
		sheets=[
			SheetInput(
				name="Лист",
				width_mm=1000,
				height_mm=1000,
				margins=SheetMargins(left_mm=10, top_mm=20, right_mm=10, bottom_mm=20),
			)
		],
		settings=CutSettings(kerf_width_mm=4),
	)

	metrics = result.sheets[0].metrics

	assert metrics.sheet_area_mm2 == 1000000
	assert metrics.usable_area_mm2 == 940800
	assert metrics.placed_area_mm2 == 10000
	assert metrics.material_utilization_percent == 1
	assert metrics.working_area_efficiency_percent == 10000 / 940800 * 100
	assert metrics.placed_area_mm2 + metrics.waste_area_mm2 + metrics.kerf_area_mm2 == metrics.usable_area_mm2


def test_multi_pass_optimization_is_deterministic() -> None:
	parts = [
		_part("1", 700, 400, quantity=2),
		_part("2", 500, 300, quantity=3),
		_part("3", 200, 150, quantity=4),
	]
	sheets = [SheetInput(name="Лист", width_mm=1200, height_mm=1000, quantity=2)]
	settings = CutSettings(kerf_width_mm=4)

	first = optimize_guillotine_cutting(parts=parts, sheets=sheets, settings=settings)
	second = optimize_guillotine_cutting(parts=parts, sheets=sheets, settings=settings)

	assert first == second
	assert first.optimization is not None
	assert first.optimization.evaluated_variant_count == 24


def test_local_suffix_rebuild_reduces_sheet_count() -> None:
	parts = [
		_part(str(index), l_mm, w_mm)
		for index, (l_mm, w_mm) in enumerate(
			(
				(54, 66),
				(74, 30),
				(58, 54),
				(50, 74),
				(26, 70),
				(34, 78),
				(70, 66),
				(42, 34),
				(34, 38),
				(46, 78),
			),
			start=1,
		)
	]

	result = optimize_guillotine_cutting(
		parts=parts,
		sheets=[SheetInput(name="Лист", width_mm=100, height_mm=100, quantity=8)],
		settings=CutSettings(kerf_width_mm=2),
	)

	assert result.metrics.placed_part_count == 10
	assert result.metrics.unplaced_part_count == 0
	assert result.metrics.sheet_count == 4
	assert result.optimization is not None
	assert result.optimization.evaluated_variant_count == 96
	assert result.optimization.selected_variant_id.startswith(
		"local_suffix_3_to_2__"
	)


def test_basis_reference_local_rebuild_reaches_13_sheets() -> None:
	result = optimize_guillotine_cutting(
		parts=build_basis_agt_3019_parts(),
		sheets=build_basis_agt_3019_sheets(),
		settings=build_basis_agt_3019_settings(),
	)

	assert result.metrics.placed_part_count == 93
	assert result.metrics.unplaced_part_count == 0
	assert result.metrics.sheet_count == 13
	assert round(result.metrics.material_utilization_percent, 2) == 88.28
	assert round(result.metrics.working_area_efficiency_percent, 2) == 90.72
	assert result.optimization is not None
	assert result.optimization.evaluated_variant_count == 168
	assert result.optimization.selected_variant_id.startswith(
		"local_suffix_7_to_6__"
	)
	placed_part_numbers = [
		part.part_number
		for sheet in result.sheets
		for part in sheet.placed_parts
	]
	assert len(set(placed_part_numbers)) == 93
	assert result.edge_consumption.segment_count == 372
	assert result.edge_consumption.total_length_mm == 261526

	production_metrics = [
		sheet.production_cut_plan.metrics
		for sheet in result.sheets
		if sheet.production_cut_plan is not None
	]

	assert sum(metrics.cut_length_mm for metrics in production_metrics) == 214108
	assert sum(metrics.pass_count for metrics in production_metrics) == 236
	assert sum(metrics.strip_turn_count for metrics in production_metrics) == 97
	assert sum(metrics.size_setting_count for metrics in production_metrics) == 157
	assert validate_cutting_result(result) == []
