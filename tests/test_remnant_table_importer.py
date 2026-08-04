from cutting_app.app.domain.sheet import SheetMargins
from cutting_app.app.importers.remnant_table_importer import (
	EditableRemnantRow,
	parse_editable_remnant_rows,
)


def test_remnant_rows_build_prioritized_sheet_inputs_with_common_margins() -> None:
	result = parse_editable_remnant_rows(
		(
			EditableRemnantRow(width_mm="1000", height_mm="2000", quantity="1"),
			EditableRemnantRow(width_mm="1200", height_mm="1200", quantity="2"),
		),
		margins=SheetMargins(left_mm=15, top_mm=10, right_mm=15, bottom_mm=10),
	)

	assert result.errors == []
	assert [sheet.name for sheet in result.sheets] == [
		"Дополнительный кусок 1",
		"Дополнительный кусок 2",
	]
	assert [sheet.quantity for sheet in result.sheets] == [1, 2]
	assert all(sheet.is_remnant for sheet in result.sheets)
	assert result.sheets[0].margins.left_mm == 15
	assert result.sheets[0].margins.top_mm == 10


def test_completely_empty_remnant_row_is_ignored() -> None:
	result = parse_editable_remnant_rows(
		(EditableRemnantRow(),),
		margins=SheetMargins(),
	)

	assert result.sheets == []
	assert result.errors == []


def test_partially_filled_remnant_row_returns_explicit_error() -> None:
	result = parse_editable_remnant_rows(
		(EditableRemnantRow(width_mm="1000", height_mm="", quantity="1"),),
		margins=SheetMargins(),
	)

	assert result.sheets == []
	assert len(result.errors) == 1
	assert result.errors[0].row_number == 1
	assert "Высота" in result.errors[0].message


def test_remnant_row_rejects_area_consumed_by_common_margins() -> None:
	result = parse_editable_remnant_rows(
		(EditableRemnantRow(width_mm="20", height_mm="100", quantity="1"),),
		margins=SheetMargins(left_mm=10, right_mm=10),
	)

	assert result.sheets == []
	assert len(result.errors) == 1
	assert "Полезная ширина" in result.errors[0].message
