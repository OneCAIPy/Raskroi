from cutting_app.app.examples.demo_cutting_orders import build_demo_order_with_unplaced_part


def test_demo_order_has_parts_sheets_and_settings() -> None:
	order = build_demo_order_with_unplaced_part()

	assert order.name
	assert len(order.parts) == 3
	assert len(order.sheets) == 2
	assert order.settings.kerf_width_mm == 4


def test_demo_order_contains_deliberately_unplaced_part() -> None:
	order = build_demo_order_with_unplaced_part()

	part_numbers = [part.number for part in order.parts]

	assert "ERR" in part_numbers


def test_demo_order_places_remnant_before_standard_sheet() -> None:
	order = build_demo_order_with_unplaced_part()

	assert order.sheets[0].is_remnant is True
	assert order.sheets[1].is_remnant is False
