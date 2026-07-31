from cutting_app.app.domain.cut_tree import (
	CutDirection,
	CutLine,
	CutNode,
	RectArea,
)
from cutting_app.app.domain.production_cut_plan import SawPassType
from cutting_app.app.services.production_cut_plan_builder import (
	build_production_cut_plan,
)


def test_same_direction_tree_chain_becomes_one_parallel_cycle():
	root = CutNode(
		area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100),
		cut=CutLine(
			direction=CutDirection.HORIZONTAL,
			position_mm=30,
			kerf_width_mm=4,
		),
	)
	root.first = CutNode(
		area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=30),
		part_number="1",
	)
	root.second = CutNode(
		area=RectArea(x_mm=0, y_mm=34, width_mm=100, height_mm=66),
		cut=CutLine(
			direction=CutDirection.HORIZONTAL,
			position_mm=64,
			kerf_width_mm=4,
		),
	)
	root.second.first = CutNode(
		area=RectArea(x_mm=0, y_mm=34, width_mm=100, height_mm=30),
		part_number="2",
	)
	root.second.second = CutNode(
		area=RectArea(x_mm=0, y_mm=68, width_mm=100, height_mm=32),
		is_waste=True,
	)

	plan = build_production_cut_plan(
		plan_id="sheet-1",
		sheet_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100),
		root=root,
		nominal_kerf_width_mm=4,
	)

	assert plan.metrics.cycle_count == 1
	assert plan.metrics.size_setting_count == 1
	assert plan.metrics.pass_count == 2
	assert plan.metrics.cut_length_mm == 200
	assert [setting.size_mm for setting in plan.size_settings] == [30]

	cycle = plan.cycles[0]

	assert len(cycle.outputs) == 2
	assert [output.part_number for output in cycle.outputs] == ["1", "2"]
	assert [output.is_waste for output in cycle.outputs] == [False, False]
	assert [saw_pass.pass_type for saw_pass in cycle.saw_passes] == [
		SawPassType.SPLIT,
		SawPassType.END_TRIM,
	]
	assert [saw_pass.y1_mm for saw_pass in cycle.saw_passes] == [30, 64]


def test_plan_uses_full_sheet_for_trims_and_links_nested_cycle():
	root = CutNode(
		area=RectArea(x_mm=10, y_mm=15, width_mm=80, height_mm=170),
		cut=CutLine(
			direction=CutDirection.HORIZONTAL,
			position_mm=75,
			kerf_width_mm=4,
		),
	)
	root.first = CutNode(
		area=RectArea(x_mm=10, y_mm=15, width_mm=80, height_mm=60),
		cut=CutLine(
			direction=CutDirection.VERTICAL,
			position_mm=50,
			kerf_width_mm=4,
		),
	)
	root.first.first = CutNode(
		area=RectArea(x_mm=10, y_mm=15, width_mm=40, height_mm=60),
		part_number="1",
	)
	root.first.second = CutNode(
		area=RectArea(x_mm=54, y_mm=15, width_mm=36, height_mm=60),
		is_waste=True,
	)
	root.second = CutNode(
		area=RectArea(x_mm=10, y_mm=79, width_mm=80, height_mm=106),
		is_waste=True,
	)

	plan = build_production_cut_plan(
		plan_id="sheet-1",
		sheet_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=200),
		root=root,
		nominal_kerf_width_mm=4,
	)

	assert plan.metrics.cycle_count == 2
	assert plan.metrics.strip_turn_count == 1
	assert plan.metrics.size_setting_count == 2
	assert plan.metrics.pass_count == 4
	assert plan.metrics.cut_length_mm == 320
	assert plan.metrics.nominal_cut_area_mm2 == 1280
	assert plan.metrics.actual_removed_area_mm2 == 1280

	first_cycle, second_cycle = plan.cycles

	assert first_cycle.direction == CutDirection.HORIZONTAL
	assert first_cycle.source_area == RectArea(
		x_mm=0,
		y_mm=0,
		width_mm=100,
		height_mm=200,
	)
	assert [saw_pass.pass_type for saw_pass in first_cycle.saw_passes] == [
		SawPassType.START_TRIM,
		SawPassType.END_TRIM,
	]
	assert [saw_pass.length_mm for saw_pass in first_cycle.saw_passes] == [100, 100]

	assert second_cycle.direction == CutDirection.VERTICAL
	assert second_cycle.source_area == RectArea(
		x_mm=0,
		y_mm=15,
		width_mm=100,
		height_mm=60,
	)
	assert second_cycle.parent_cycle_id == first_cycle.cycle_id
	assert second_cycle.source_output_id == first_cycle.outputs[0].output_id
	assert [saw_pass.length_mm for saw_pass in second_cycle.saw_passes] == [60, 60]

	assert len(plan.strip_turns) == 1
	assert [setting.size_mm for setting in plan.size_settings] == [60, 40]

	strip_turn = plan.strip_turns[0]

	assert strip_turn.source_output_id == second_cycle.source_output_id
	assert strip_turn.source_area == second_cycle.source_area
	assert strip_turn.from_cycle_id == first_cycle.cycle_id
	assert strip_turn.to_cycle_id == second_cycle.cycle_id
	assert strip_turn.from_direction == CutDirection.HORIZONTAL
	assert strip_turn.to_direction == CutDirection.VERTICAL
	assert strip_turn.angle_degrees == 90


def test_exact_usable_leaf_uses_explicit_initial_direction_for_sheet_trims():
	root = CutNode(
		area=RectArea(x_mm=10, y_mm=20, width_mm=80, height_mm=60),
		part_number="1",
	)

	plan = build_production_cut_plan(
		plan_id="sheet-1",
		sheet_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100),
		root=root,
		nominal_kerf_width_mm=4,
		initial_direction=CutDirection.HORIZONTAL,
	)

	assert [cycle.direction for cycle in plan.cycles] == [
		CutDirection.HORIZONTAL,
		CutDirection.VERTICAL,
	]
	assert plan.metrics.cycle_count == 2
	assert plan.metrics.strip_turn_count == 1
	assert plan.metrics.size_setting_count == 2
	assert plan.metrics.pass_count == 4
	assert plan.metrics.cut_length_mm == 320
	assert [setting.size_mm for setting in plan.size_settings] == [60, 80]
