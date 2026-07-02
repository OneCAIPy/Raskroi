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
	assert second.x_mm == 404
	assert second.x_mm - (first.x_mm + first.width_mm) == 4
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
