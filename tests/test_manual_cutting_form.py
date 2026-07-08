from cutting_app.app.web.manual_cutting_form import (
	ManualCuttingFormData,
	build_manual_cutting_preview,
	make_default_manual_cutting_form,
	manual_cutting_form_from_urlencoded_body,
)


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
		"margin_left_mm=1&margin_top_mm=2&margin_right_mm=3&margin_bottom_mm=4&"
		"parts_text=A1%3B+Part%3B+100%3B+50%3B+1"
	).encode("utf-8")

	form = manual_cutting_form_from_urlencoded_body(body)

	assert form.sheet_width_mm == "1000"
	assert form.sheet_quantity == "2"
	assert form.margin_bottom_mm == "4"
	assert form.parts_text == "A1; Part; 100; 50; 1"
