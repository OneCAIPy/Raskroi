from io import BytesIO

from openpyxl import Workbook

from cutting_app.app.importers.parts_xlsx_importer import import_parts_xlsx
from cutting_app.app.importers.parts_table_importer import parse_editable_part_rows
from cutting_app.app.services.edge_consumption_calculator import (
	build_part_edge_segments,
	summarize_edge_segments,
)
from tests.basis_agt_3019_fixture import BASIS_AGT_3019_PARTS


TEMPLATE_HEADERS = [
	"Кроить",
	"Материал",
	"Позиция",
	"Наименования",
	"Длинна",
	"Ширина",
	"Колличество",
	"Ориентация",
	"L1 - Обозн.",
	"L2 - Обозн.",
	"W1 - Обозн.",
	"W2 - Обозн.",
]


def test_import_parts_xlsx_reads_template_rows_and_edge_marks() -> None:
	contents = _make_xlsx(
		TEMPLATE_HEADERS,
		[
			["Да", "АГТ 3019", 1, None, 401, 801, 2, "Не задана", "*", "*", "*", "*"],
			["Да", "АГТ 3019", "A2", "Полка", 600.5, 300, 3, None, "*", None, None, "*"],
			["Нет", "АГТ 3019", 3, "Не кроить", 100, 100, 1, None, "*", "*", "*", "*"],
		],
	)

	result = import_parts_xlsx(contents, filename="деталировка.xlsx")

	assert result.errors == []
	assert result.filename == "деталировка.xlsx"
	assert result.sheet_name == "Лист1"
	assert result.skipped_row_count == 1
	assert len(result.rows) == 2
	assert result.rows[0].number == "1"
	assert result.rows[0].name == "Позиция 1"
	assert result.rows[0].l_mm == "401"
	assert result.rows[0].w_mm == "801"
	assert result.rows[0].quantity == "2"
	assert result.rows[0].rotation_allowed
	assert result.rows[0].L1
	assert result.rows[0].L2
	assert result.rows[0].W1
	assert result.rows[0].W2
	assert result.rows[1].number == "A2"
	assert result.rows[1].name == "Полка"
	assert result.rows[1].l_mm == "600.5"
	assert result.rows[1].L1
	assert not result.rows[1].L2
	assert not result.rows[1].W1
	assert result.rows[1].W2


def test_import_parts_xlsx_accepts_correctly_spelled_headers() -> None:
	contents = _make_xlsx(
		["Номер", "Название", "Длина", "Ширина", "Количество", "L1", "L2", "W1", "W2"],
		[["A1", "Фасад", 720, 500, 2, "*", None, None, "*"]],
	)

	result = import_parts_xlsx(contents)

	assert result.errors == []
	assert len(result.rows) == 1
	assert result.rows[0].number == "A1"
	assert result.rows[0].name == "Фасад"
	assert result.rows[0].L1
	assert result.rows[0].W2


def test_import_parts_xlsx_reports_missing_required_headers() -> None:
	contents = _make_xlsx(
		["Позиция", "Длинна", "Колличество"],
		[[1, 400, 2]],
	)

	result = import_parts_xlsx(contents)

	assert result.rows == []
	assert len(result.errors) == 1
	assert "Ширина" in result.errors[0].message


def test_import_parts_xlsx_reports_unknown_edge_marker_without_guessing() -> None:
	contents = _make_xlsx(
		TEMPLATE_HEADERS,
		[["Да", "АГТ 3019", 1, None, 401, 801, 2, "Не задана", "Кромка", None, None, None]],
	)

	result = import_parts_xlsx(contents)

	assert len(result.rows) == 1
	assert len(result.errors) == 1
	assert result.errors[0].table_row_number == 1
	assert "L1" in result.errors[0].message
	assert "Кромка" in result.errors[0].message
	assert not result.rows[0].L1


def test_import_parts_xlsx_reports_corrupted_file() -> None:
	result = import_parts_xlsx(b"not an xlsx file", filename="broken.xlsx")

	assert result.rows == []
	assert len(result.errors) == 1
	assert "не удалось открыть" in result.errors[0].message.lower()


def test_import_parts_xlsx_preserves_basis_reference_edge_totals() -> None:
	contents = _make_xlsx(
		TEMPLATE_HEADERS,
		[
			[
				"Да",
				"АГТ 3019",
				position,
				None,
				l_mm,
				w_mm,
				quantity,
				"Не задана",
				"*",
				"*",
				"*",
				"*",
			]
			for position, l_mm, w_mm, quantity in BASIS_AGT_3019_PARTS
		],
	)

	xlsx_result = import_parts_xlsx(contents)
	parts_result = parse_editable_part_rows(
		xlsx_result.rows,
		edge_thickness_mm="1",
		edge_trimming_allowance_mm="0,5",
		edge_material_name="3019 АГТ Кромка Abs 22*1",
	)
	segments = []
	for part in parts_result.parts:
		for instance_number in range(1, part.quantity + 1):
			segments.extend(
				build_part_edge_segments(
					part,
					part_number=f"{part.number}-{instance_number}",
				)
			)
	edge_consumption = summarize_edge_segments(segments)

	assert xlsx_result.errors == []
	assert parts_result.errors == []
	assert len(parts_result.parts) == 53
	assert sum(part.quantity for part in parts_result.parts) == 93
	assert edge_consumption.segment_count == 372
	assert edge_consumption.total_length_mm == 261526


def _make_xlsx(headers: list[object], rows: list[list[object]]) -> bytes:
	workbook = Workbook()
	worksheet = workbook.active
	worksheet.title = "Лист1"
	worksheet.append(headers)
	for row in rows:
		worksheet.append(row)

	buffer = BytesIO()
	workbook.save(buffer)
	return buffer.getvalue()
