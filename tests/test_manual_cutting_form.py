import pytest

from cutting_app.app.domain.return_remnant import ReturnRemnantProfile
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
	assert preview.result.optimization.score.cut_length_mm == 216706.2
	assert preview.result.optimization.score.pass_count == 235
	assert preview.result.optimization.score.strip_turn_count == 100
	assert preview.result.optimization.score.size_setting_count == 162
	assert len(preview.result.return_remnants) == 17
	assert preview.result.metrics.return_remnant_area_mm2 == pytest.approx(1_944_417.68)
	assert (
		preview.result.metrics.material_utilization_with_return_remnants_percent
		== pytest.approx(92.65519879301026)
	)
