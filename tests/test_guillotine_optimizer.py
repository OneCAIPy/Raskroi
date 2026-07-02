from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cut_tree import CutDirection
from cutting_app.app.domain.edge import EdgeSet
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting


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
		parts=[_part("1", 700, 200)],
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
