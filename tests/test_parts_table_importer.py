from cutting_app.app.importers.parts_table_importer import (
	EditablePartRow,
	parse_editable_part_rows,
)


def test_parse_editable_part_rows_applies_common_edge_settings() -> None:
	result = parse_editable_part_rows(
		[
			EditablePartRow(
				number="12",
				name="Фасад",
				l_mm="400",
				w_mm="800",
				quantity="2",
				rotation_allowed=False,
				L1=True,
				W2=True,
			)
		],
		edge_thickness_mm="1",
		edge_trimming_allowance_mm="0,5",
		edge_material_name="ABS белая",
	)

	assert result.errors == []
	assert len(result.parts) == 1
	part = result.parts[0]
	assert part.number == "12"
	assert part.name == "Фасад"
	assert part.l_mm == 400
	assert part.w_mm == 800
	assert part.quantity == 2
	assert not part.rotation_allowed
	assert part.edges.L1.thickness_mm == 1
	assert part.edges.L1.trimming_allowance_mm == 0.5
	assert part.edges.L1.material_name == "ABS белая"
	assert not part.edges.L2.has_edge
	assert not part.edges.W1.has_edge
	assert part.edges.W2.has_edge


def test_parse_editable_part_rows_reports_row_and_common_edge_errors() -> None:
	result = parse_editable_part_rows(
		[
			EditablePartRow(
				number="",
				name="",
				l_mm="bad",
				w_mm="800",
				quantity="0",
				L1=True,
			)
		],
		edge_thickness_mm="0",
		edge_trimming_allowance_mm="-0,5",
		edge_material_name="",
	)

	assert result.parts == []
	assert len(result.errors) == 1
	assert result.errors[0].row_number == 1
	assert "Номер детали" in result.errors[0].message
	assert "Название детали" in result.errors[0].message
	assert "Поле L должно быть числом" in result.errors[0].message
	assert "количество" in result.errors[0].message
	assert "Толщина кромки" in result.errors[0].message
	assert "Прифуговка" in result.errors[0].message


def test_parse_editable_part_rows_does_not_require_edge_settings_without_edges() -> None:
	result = parse_editable_part_rows(
		[
			EditablePartRow(
				number="1",
				name="Полка",
				l_mm="600",
				w_mm="300",
				quantity="1",
			)
		],
		edge_thickness_mm="",
		edge_trimming_allowance_mm="",
		edge_material_name="",
	)

	assert result.errors == []
	assert len(result.parts) == 1
	assert not result.parts[0].edges.L1.has_edge
