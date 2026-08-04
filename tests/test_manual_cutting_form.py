import pytest

from cutting_app.app.domain.return_remnant import ReturnRemnantProfile
from cutting_app.app.importers.parts_table_importer import EditablePartRow
from cutting_app.app.importers.remnant_table_importer import EditableRemnantRow
from cutting_app.app.web.manual_cutting_form import (
	ManualCuttingFormData,
	build_manual_cutting_preview,
	make_default_manual_cutting_form,
	manual_cutting_form_from_urlencoded_body,
)
from tests.basis_agt_3019_fixture import BASIS_AGT_3019_PARTS


def test_manual_cutting_preview_builds_svg_for_valid_form() -> None:
	preview = build_manual_cutting_preview(make_default_manual_cutting_form())

	assert preview.input_errors == []
	assert preview.result is not None
	assert preview.svg is not None
	assert "placed-part" in preview.svg
	assert preview.result.metrics.placed_part_count == 7


def test_manual_cutting_preview_reports_input_errors_without_svg() -> None:
	form = ManualCuttingFormData(
		sheet_width_mm="0",
		sheet_height_mm="2070",
		sheet_quantity="1",
		kerf_width_mm="4",
		margin_left_mm="10",
		margin_top_mm="10",
		margin_right_mm="10",
		margin_bottom_mm="10",
		parts_text="A1; Ошибка; 720; 500",
	)

	preview = build_manual_cutting_preview(form)

	assert preview.result is None
	assert preview.svg is None
	assert any("Ширина листа" in error for error in preview.input_errors)
	assert any("Строка 1" in error for error in preview.input_errors)


def test_manual_cutting_form_from_urlencoded_body_reads_posted_values() -> None:
	body = (
		"sheet_width_mm=1000&sheet_height_mm=800&sheet_quantity=2&kerf_width_mm=3&"
		"initial_cut_direction=horizontal&"
		"return_remnant_profile=long&"
		"return_remnant_min_long_side_mm=450&return_remnant_min_short_side_mm=90&"
		"return_remnant_min_area_m2=0%2C05&"
		"margin_left_mm=1&margin_top_mm=2&margin_right_mm=3&margin_bottom_mm=4&"
		"parts_text=A1%3B+Part%3B+100%3B+50%3B+1"
	).encode("utf-8")

	form = manual_cutting_form_from_urlencoded_body(body)

	assert form.sheet_width_mm == "1000"
	assert form.sheet_quantity == "2"
	assert form.initial_cut_direction == "horizontal"
	assert form.return_remnant_profile == "long"
	assert form.return_remnant_min_long_side_mm == "450"
	assert form.return_remnant_min_short_side_mm == "90"
	assert form.return_remnant_min_area_m2 == "0,05"
	assert form.margin_bottom_mm == "4"
	assert form.parts_text == "A1; Part; 100; 50; 1"


def test_manual_cutting_form_from_urlencoded_body_reads_editable_table() -> None:
	body = (
		"sheet_width_mm=1000&sheet_height_mm=800&sheet_quantity=2&kerf_width_mm=3&"
		"margin_left_mm=1&margin_top_mm=2&margin_right_mm=3&margin_bottom_mm=4&"
		"parts_input_mode=table&edge_thickness_mm=1&"
		"edge_trimming_allowance_mm=0%2C5&edge_material_name=ABS+white&"
		"part_0_number=A1&part_0_name=Front&part_0_l_mm=400&part_0_w_mm=800&"
		"part_0_quantity=2&part_0_rotation_allowed=on&part_0_L1=on&part_0_W2=on&"
		"part_2_number=A2&part_2_name=Shelf&part_2_l_mm=600&part_2_w_mm=300&"
		"part_2_quantity=1"
	).encode("utf-8")

	form = manual_cutting_form_from_urlencoded_body(body)

	assert form.parts_input_mode == "table"
	assert form.edge_thickness_mm == "1"
	assert form.edge_trimming_allowance_mm == "0,5"
	assert form.edge_material_name == "ABS white"
	assert len(form.part_rows) == 2
	assert form.part_rows[0].number == "A1"
	assert form.part_rows[0].rotation_allowed
	assert form.part_rows[0].L1
	assert form.part_rows[0].W2
	assert form.part_rows[1].number == "A2"
	assert not form.part_rows[1].rotation_allowed


def test_manual_cutting_form_defaults_to_requested_stock_and_kerf_values() -> None:
	form = make_default_manual_cutting_form()

	assert form.sheet_quantity == "100"
	assert form.kerf_width_mm == "4,4"


def test_manual_cutting_form_from_urlencoded_body_reads_additional_pieces() -> None:
	body = (
		"sheet_width_mm=2800&sheet_height_mm=1220&sheet_quantity=100&kerf_width_mm=4%2C4&"
		"margin_left_mm=10&margin_top_mm=10&margin_right_mm=10&margin_bottom_mm=10&"
		"remnant_0_width_mm=1000&remnant_0_height_mm=2000&remnant_0_quantity=1&"
		"remnant_2_width_mm=1200&remnant_2_height_mm=1200&remnant_2_quantity=2"
	).encode("utf-8")

	form = manual_cutting_form_from_urlencoded_body(body)

	assert form.remnant_rows == (
		EditableRemnantRow(width_mm="1000", height_mm="2000", quantity="1"),
		EditableRemnantRow(width_mm="1200", height_mm="1200", quantity="2"),
	)


def test_manual_cutting_preview_uses_additional_piece_before_standard_sheet() -> None:
	default_form = make_default_manual_cutting_form()
	form = ManualCuttingFormData(
		sheet_width_mm="1000",
		sheet_height_mm="1000",
		sheet_quantity="1",
		kerf_width_mm="4",
		margin_left_mm="0",
		margin_top_mm="0",
		margin_right_mm="0",
		margin_bottom_mm="0",
		parts_text="A1; Полка; 400; 400; 2",
		remnant_rows=(
			EditableRemnantRow(width_mm="500", height_mm="500", quantity="1"),
		),
	)

	preview = build_manual_cutting_preview(form)

	assert preview.input_errors == []
	assert preview.result is not None
	assert preview.result.metrics.sheet_count == 2
	assert preview.result.metrics.standard_sheet_count == 1
	assert preview.result.metrics.input_remnant_count == 1
	assert [sheet.sheet_is_remnant for sheet in preview.result.sheets] == [True, False]
	assert preview.result.sheets[0].sheet_stock_name == "Дополнительный кусок 1"


def test_manual_cutting_preview_reports_invalid_additional_piece_row() -> None:
	default_form = make_default_manual_cutting_form()
	form = ManualCuttingFormData(
		sheet_width_mm=default_form.sheet_width_mm,
		sheet_height_mm=default_form.sheet_height_mm,
		sheet_quantity=default_form.sheet_quantity,
		kerf_width_mm=default_form.kerf_width_mm,
		margin_left_mm=default_form.margin_left_mm,
		margin_top_mm=default_form.margin_top_mm,
		margin_right_mm=default_form.margin_right_mm,
		margin_bottom_mm=default_form.margin_bottom_mm,
		parts_text=default_form.parts_text,
		remnant_rows=(
			EditableRemnantRow(width_mm="1000", height_mm="", quantity="1"),
		),
	)

	preview = build_manual_cutting_preview(form)

	assert preview.result is None
	assert preview.remnant_row_error_numbers == (1,)
	assert any("Дополнительный кусок 1" in error for error in preview.input_errors)


def test_manual_cutting_preview_passes_return_remnant_profile_to_optimizer() -> None:
	default_form = make_default_manual_cutting_form()
	form = ManualCuttingFormData(
		sheet_width_mm=default_form.sheet_width_mm,
		sheet_height_mm=default_form.sheet_height_mm,
		sheet_quantity=default_form.sheet_quantity,
		kerf_width_mm=default_form.kerf_width_mm,
		margin_left_mm=default_form.margin_left_mm,
		margin_top_mm=default_form.margin_top_mm,
		margin_right_mm=default_form.margin_right_mm,
		margin_bottom_mm=default_form.margin_bottom_mm,
		parts_text=default_form.parts_text,
		return_remnant_profile=ReturnRemnantProfile.COMPACT.value,
	)

	preview = build_manual_cutting_preview(form)

	assert preview.input_errors == []
	assert preview.result is not None
	assert preview.result.optimization is not None
	assert (
		preview.result.optimization.score.return_remnant_profile
		== ReturnRemnantProfile.COMPACT
	)


def test_manual_cutting_preview_reports_invalid_return_remnant_profile() -> None:
	default_form = make_default_manual_cutting_form()
	form = ManualCuttingFormData(
		sheet_width_mm=default_form.sheet_width_mm,
		sheet_height_mm=default_form.sheet_height_mm,
		sheet_quantity=default_form.sheet_quantity,
		kerf_width_mm=default_form.kerf_width_mm,
		margin_left_mm=default_form.margin_left_mm,
		margin_top_mm=default_form.margin_top_mm,
		margin_right_mm=default_form.margin_right_mm,
		margin_bottom_mm=default_form.margin_bottom_mm,
		parts_text=default_form.parts_text,
		return_remnant_profile="triangle",
	)

	preview = build_manual_cutting_preview(form)

	assert preview.result is None
	assert preview.svg is None
	assert any(
		"Профиль возвратного остатка" in error
		for error in preview.input_errors
	)


def test_manual_cutting_preview_reports_invalid_initial_cut_direction() -> None:
	default_form = make_default_manual_cutting_form()
	form = ManualCuttingFormData(
		sheet_width_mm=default_form.sheet_width_mm,
		sheet_height_mm=default_form.sheet_height_mm,
		sheet_quantity=default_form.sheet_quantity,
		kerf_width_mm=default_form.kerf_width_mm,
		margin_left_mm=default_form.margin_left_mm,
		margin_top_mm=default_form.margin_top_mm,
		margin_right_mm=default_form.margin_right_mm,
		margin_bottom_mm=default_form.margin_bottom_mm,
		parts_text=default_form.parts_text,
		initial_cut_direction="diagonal",
	)

	preview = build_manual_cutting_preview(form)

	assert preview.result is None
	assert preview.svg is None
	assert any("Первое направление" in error for error in preview.input_errors)


def test_manual_cutting_preview_uses_editable_table_and_common_edge_settings() -> None:
	default_form = make_default_manual_cutting_form()
	form = ManualCuttingFormData(
		sheet_width_mm="1000",
		sheet_height_mm="1000",
		sheet_quantity="1",
		kerf_width_mm="4",
		margin_left_mm="0",
		margin_top_mm="0",
		margin_right_mm="0",
		margin_bottom_mm="0",
		parts_text=default_form.parts_text,
		parts_input_mode="table",
		edge_thickness_mm="1",
		edge_trimming_allowance_mm="0,5",
		edge_material_name="ABS белая",
		part_rows=(
			EditablePartRow(
				number="A1",
				name="Фасад",
				l_mm="300",
				w_mm="800",
				quantity="1",
				L1=True,
				L2=True,
				W1=True,
				W2=True,
			),
		),
	)

	preview = build_manual_cutting_preview(form)

	assert preview.input_errors == []
	assert preview.result is not None
	assert preview.result.metrics.placed_part_count == 1
	assert preview.result.edge_consumption.segment_count == 4
	assert preview.result.edge_consumption.base_length_mm == 2200
	assert preview.result.edge_consumption.by_material[0].material_name == "ABS белая"


def test_manual_cutting_preview_rejects_inverted_return_remnant_sides() -> None:
	default_form = make_default_manual_cutting_form()
	form = ManualCuttingFormData(
		sheet_width_mm=default_form.sheet_width_mm,
		sheet_height_mm=default_form.sheet_height_mm,
		sheet_quantity=default_form.sheet_quantity,
		kerf_width_mm=default_form.kerf_width_mm,
		margin_left_mm=default_form.margin_left_mm,
		margin_top_mm=default_form.margin_top_mm,
		margin_right_mm=default_form.margin_right_mm,
		margin_bottom_mm=default_form.margin_bottom_mm,
		parts_text=default_form.parts_text,
		return_remnant_min_long_side_mm="70",
		return_remnant_min_short_side_mm="80",
	)

	preview = build_manual_cutting_preview(form)

	assert preview.result is None
	assert preview.svg is None
	assert any(
		"длинная сторона не может быть меньше короткой" in error
		for error in preview.input_errors
	)


def test_basis_reference_passes_through_extended_manual_input() -> None:
	edge = "1|0,5|0|3019 АГТ Кромка Abs 22*1"
	parts_text = "\n".join(
		f"{position}; Позиция {position}; {l_mm}; {w_mm}; {quantity}; "
		f"{edge}; {edge}; {edge}; {edge}"
		for position, l_mm, w_mm, quantity in BASIS_AGT_3019_PARTS
	)
	form = ManualCuttingFormData(
		sheet_width_mm="2800",
		sheet_height_mm="1220",
		sheet_quantity="20",
		kerf_width_mm="4,4",
		margin_left_mm="15",
		margin_top_mm="10",
		margin_right_mm="15",
		margin_bottom_mm="10",
		parts_text=parts_text,
	)

	preview = build_manual_cutting_preview(form)

	assert preview.input_errors == []
	assert preview.issues == []
	assert preview.result is not None
	assert preview.result.metrics.placed_part_count == 93
	assert preview.result.metrics.sheet_count == 13
	assert preview.result.edge_consumption.segment_count == 372
	assert preview.result.edge_consumption.total_length_mm == 261526
	assert preview.result.optimization is not None
	assert (
		preview.result.optimization.score.return_remnant_profile
		== ReturnRemnantProfile.MAX_USEFUL_AREA
	)
	assert preview.result.optimization.score.cut_length_mm == pytest.approx(216921.2)
	assert preview.result.optimization.score.pass_count == 231
	assert preview.result.optimization.score.strip_turn_count == 97
	assert preview.result.optimization.score.size_setting_count == 161
	assert len(preview.result.return_remnants) == 17
	assert preview.result.metrics.return_remnant_area_mm2 == pytest.approx(2_083_414.56)
	assert (
		preview.result.metrics.material_utilization_with_return_remnants_percent
		== pytest.approx(92.96819843271483)
	)
