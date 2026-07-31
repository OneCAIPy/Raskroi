from cutting_app.app.examples.demo_cutting_orders import (
	build_demo_order_realistic_cabinet,
	build_demo_order_simple_without_errors,
	build_demo_order_with_remnant,
	build_demo_order_with_rotation_and_edges,
	build_demo_order_with_unplaced_part,
	find_demo_cutting_order,
	list_demo_cutting_orders,
)
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting


def test_demo_orders_are_listed() -> None:
	orders = list_demo_cutting_orders()

	assert len(orders) == 5


def test_demo_orders_have_unique_names() -> None:
	orders = list_demo_cutting_orders()

	names = [order.name for order in orders]

	assert len(names) == len(set(names))


def test_demo_orders_have_unique_slugs() -> None:
	orders = list_demo_cutting_orders()

	slugs = [order.slug for order in orders]

	assert len(slugs) == len(set(slugs))


def test_demo_order_can_be_found_by_slug() -> None:
	order = find_demo_cutting_order("cabinet")

	assert order.name == "Почти реальный корпусный заказ"


def test_unknown_demo_order_slug_raises_error() -> None:
	try:
		find_demo_cutting_order("missing")
	except ValueError as error:
		assert "missing" in str(error)
	else:
		raise AssertionError("Expected ValueError for unknown demo order slug")


def test_demo_order_with_unplaced_part_keeps_deliberate_error() -> None:
	order = build_demo_order_with_unplaced_part()

	part_numbers = [part.number for part in order.parts]

	assert "ERR" in part_numbers


def test_demo_order_places_remnant_before_standard_sheet() -> None:
	order = build_demo_order_with_unplaced_part()

	assert order.sheets[0].is_remnant is True
	assert order.sheets[1].is_remnant is False


def test_non_error_demo_orders_can_be_optimized_without_unplaced_parts() -> None:
	for order in [
		build_demo_order_simple_without_errors(),
		build_demo_order_with_remnant(),
		build_demo_order_with_rotation_and_edges(),
		build_demo_order_realistic_cabinet(),
	]:
		result = optimize_guillotine_cutting(
			parts=order.parts,
			sheets=order.sheets,
			settings=order.settings,
		)

		assert result.metrics.unplaced_part_count == 0, order.name
		assert result.metrics.placed_part_count == sum(part.quantity for part in order.parts), order.name
		assert result.metrics.sheet_count >= 1, order.name
		assert result.metrics.material_utilization_percent > 0, order.name
		assert result.metrics.working_area_efficiency_percent > 0, order.name


def test_demo_order_with_unplaced_part_reports_one_unplaced_part() -> None:
	order = build_demo_order_with_unplaced_part()

	result = optimize_guillotine_cutting(
		parts=order.parts,
		sheets=order.sheets,
		settings=order.settings,
	)

	assert result.metrics.unplaced_part_count == 1
	assert any(part.source_part_number == "ERR" for part in result.unplaced_parts)


def test_remnant_demo_uses_remnant_first() -> None:
	order = build_demo_order_with_remnant()

	result = optimize_guillotine_cutting(
		parts=order.parts,
		sheets=order.sheets,
		settings=order.settings,
	)

	assert result.metrics.unplaced_part_count == 0
	assert result.sheets[0].sheet_name.startswith("Остаток")


def test_rotation_demo_requires_rotation_to_place_long_part() -> None:
	order = build_demo_order_with_rotation_and_edges()

	result = optimize_guillotine_cutting(
		parts=order.parts,
		sheets=order.sheets,
		settings=order.settings,
	)

	placed_parts = [
		part
		for sheet in result.sheets
		for part in sheet.placed_parts
		if part.source_part_number == "ROT1"
	]

	assert len(placed_parts) == 1
	assert placed_parts[0].width_mm < placed_parts[0].height_mm
