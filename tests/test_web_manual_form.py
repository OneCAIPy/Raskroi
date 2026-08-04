from base64 import b64decode
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from cutting_app.app.web.app import create_app


def test_manual_form_page_is_available() -> None:
	client = TestClient(create_app())

	response = client.get("/manual")

	assert response.status_code == 200
	assert "Ручной ввод раскроя" in response.text
	assert 'name="initial_cut_direction"' in response.text
	assert 'value="vertical" selected' in response.text
	assert 'name="return_remnant_min_long_side_mm"' in response.text
	assert 'name="return_remnant_min_short_side_mm"' in response.text
	assert 'name="return_remnant_min_area_m2"' in response.text
	assert 'name="return_remnant_profile"' in response.text
	assert 'value="max_useful_area" selected' in response.text
	assert 'value="long"' in response.text
	assert 'value="compact"' in response.text
	assert "Минимальная длинная сторона" in response.text
	assert 'action="/manual/import-xlsx"' in response.text
	assert 'enctype="multipart/form-data"' in response.text
	assert 'accept=".xlsx"' in response.text
	assert 'name="edge_thickness_mm"' in response.text
	assert 'name="edge_trimming_allowance_mm"' in response.text
	assert 'name="part_0_number"' in response.text
	assert "Добавить строку" in response.text
	assert "Очистить таблицу" in response.text
	assert "Дублировать" in response.text
	assert "Удалить" in response.text
	assert "textarea" in response.text
	assert "номер; название; L; W; количество; L1; L2; W1; W2" in response.text
	assert "толщина|прифуговка|свес|материал" in response.text
	assert "Рассчитать" in response.text
	assert 'name="sheet_quantity" value="100"' in response.text
	assert 'name="kerf_width_mm" value="4,4"' in response.text
	assert 'id="remnants-table"' in response.text
	assert 'name="remnant_0_width_mm"' in response.text
	assert "Добавить кусок" in response.text


def test_manual_form_post_returns_svg_result() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual",
		data={
			"sheet_width_mm": "1000",
			"sheet_height_mm": "800",
			"sheet_quantity": "1",
			"kerf_width_mm": "4",
			"initial_cut_direction": "horizontal",
			"return_remnant_profile": "long",
			"margin_left_mm": "0",
			"margin_top_mm": "0",
			"margin_right_mm": "0",
			"margin_bottom_mm": "0",
			"parts_text": "A1; Полка; 400; 300; 2",
		},
	)

	assert response.status_code == 200
	assert "Результат" in response.text
	assert "КИМ:" in response.text
	assert "Заполнение рабочей области:" in response.text
	assert "Длина кромки: 0.000 м" in response.text
	assert "Длина кромки со свесом: 0.000 м" in response.text
	assert "Отрезов кромки: 0" in response.text
	assert "Длина резов (проходов):" in response.text
	assert "Количество резов (проходов):" in response.text
	assert "Количество поворотов полос:" in response.text
	assert "Количество установок размеров:" in response.text
	assert "Количество возвратных остатков:" in response.text
	assert "Площадь возвратных остатков:" in response.text
	assert "КИМ с учётом возвратных остатков:" in response.text
	assert "Размер (длинная × короткая), мм" in response.text
	assert 'value="horizontal" selected' in response.text
	assert 'value="long" selected' in response.text
	assert "Профиль возвратного остатка: длинный остаток" in response.text
	assert "Эффективность:" not in response.text
	assert "<svg" in response.text
	assert "placed-part" in response.text
	assert 'download="raskroi-report.txt"' in response.text
	data_uri_prefix = "data:text/plain;charset=utf-8;base64,"
	report_base64 = response.text.split(data_uri_prefix, 1)[1].split('"', 1)[0]
	report = b64decode(report_base64).decode("utf-8")
	assert report.startswith("\ufeffКоличество плит материала\t1\r\n")
	assert "Количество панелей\t2\r\n" in report
	assert "Обрезки\r\n" in report
	ordered_labels = [
		"Количество плит материала:",
		"КИМ:",
		"Длина резов (проходов):",
		"Облицовка",
		"Количество карт раскроя:",
		"Профиль возвратного остатка:",
		"Возвратные остатки",
	]
	result_html = response.text.split('<section class="result">', 1)[1]
	positions = [result_html.index(label) for label in ordered_labels]
	assert positions == sorted(positions)


def test_manual_form_post_uses_additional_piece_before_standard_sheet() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual",
		data={
			"sheet_width_mm": "1000",
			"sheet_height_mm": "1000",
			"sheet_quantity": "1",
			"kerf_width_mm": "4",
			"margin_left_mm": "0",
			"margin_top_mm": "0",
			"margin_right_mm": "0",
			"margin_bottom_mm": "0",
			"parts_text": "A1; Полка; 400; 400; 2",
			"remnant_0_width_mm": "500",
			"remnant_0_height_mm": "500",
			"remnant_0_quantity": "1",
		},
	)

	assert response.status_code == 200
	assert "Количество плит материала: 1" in response.text
	assert "Количество использованных дополнительных кусков: 1" in response.text
	assert "Дополнительный кусок 1" in response.text


def test_manual_form_uploads_xlsx_into_editable_table_without_calculation() -> None:
	client = TestClient(create_app())
	contents = _make_xlsx(
		[
			"Кроить",
			"Позиция",
			"Наименования",
			"Длинна",
			"Ширина",
			"Колличество",
			"L1 - Обозн.",
			"L2 - Обозн.",
			"W1 - Обозн.",
			"W2 - Обозн.",
		],
		[["Да", 7, None, 401, 801, 2, "*", None, "*", None]],
	)

	response = client.post(
		"/manual/import-xlsx",
		files={
			"parts_xlsx": (
				"деталировка.xlsx",
				contents,
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			)
		},
	)

	assert response.status_code == 200
	assert "Загружен файл: деталировка.xlsx" in response.text
	assert 'name="part_0_number" value="7"' in response.text
	assert 'name="part_0_name" value="Позиция 7"' in response.text
	assert 'name="part_0_l_mm" value="401"' in response.text
	assert 'name="part_0_w_mm" value="801"' in response.text
	assert 'name="part_0_quantity" value="2"' in response.text
	assert 'name="part_0_L1" checked' in response.text
	assert 'name="part_0_W1" checked' in response.text
	assert "<svg" not in response.text


def test_manual_form_calculates_from_editable_table() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual",
		data={
			"sheet_width_mm": "1000",
			"sheet_height_mm": "1000",
			"sheet_quantity": "1",
			"kerf_width_mm": "4",
			"margin_left_mm": "0",
			"margin_top_mm": "0",
			"margin_right_mm": "0",
			"margin_bottom_mm": "0",
			"parts_input_mode": "table",
			"edge_thickness_mm": "1",
			"edge_trimming_allowance_mm": "0,5",
			"edge_material_name": "ABS белая",
			"part_0_number": "A1",
			"part_0_name": "Фасад",
			"part_0_l_mm": "300",
			"part_0_w_mm": "800",
			"part_0_quantity": "1",
			"part_0_rotation_allowed": "on",
			"part_0_L1": "on",
			"part_0_L2": "on",
			"part_0_W1": "on",
			"part_0_W2": "on",
		},
	)

	assert response.status_code == 200
	assert "Результат" in response.text
	assert "Длина кромки: 2.200 м" in response.text
	assert "Отрезов кромки: 4" in response.text
	assert "ABS белая" in response.text
	assert "<svg" in response.text


def test_manual_form_upload_reports_invalid_xlsx() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual/import-xlsx",
		files={"parts_xlsx": ("broken.xlsx", b"broken", "application/octet-stream")},
	)

	assert response.status_code == 200
	assert "Ошибки ввода" in response.text
	assert "не удалось открыть" in response.text.lower()


def test_manual_form_post_outputs_each_return_remnant() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual",
		data={
			"sheet_width_mm": "1000",
			"sheet_height_mm": "1000",
			"sheet_quantity": "1",
			"kerf_width_mm": "4",
			"return_remnant_min_long_side_mm": "400",
			"return_remnant_min_short_side_mm": "80",
			"return_remnant_min_area_m2": "0,04",
			"margin_left_mm": "0",
			"margin_top_mm": "0",
			"margin_right_mm": "0",
			"margin_bottom_mm": "0",
			"parts_text": "A1; Полка; 400; 400; 1",
		},
	)

	assert response.status_code == 200
	assert "Количество возвратных остатков: 2" in response.text
	assert "Площадь возвратных остатков: 0.834 м²" in response.text
	assert "КИМ с учётом возвратных остатков: 99.44%" in response.text
	assert "1000 × 596" in response.text
	assert "596 × 400" in response.text


def test_manual_form_post_applies_return_remnant_thresholds() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual",
		data={
			"sheet_width_mm": "1000",
			"sheet_height_mm": "1000",
			"sheet_quantity": "1",
			"kerf_width_mm": "4",
			"return_remnant_min_long_side_mm": "800",
			"return_remnant_min_short_side_mm": "80",
			"return_remnant_min_area_m2": "0,04",
			"margin_left_mm": "0",
			"margin_top_mm": "0",
			"margin_right_mm": "0",
			"margin_bottom_mm": "0",
			"parts_text": "A1; Полка; 400; 400; 1",
		},
	)

	assert response.status_code == 200
	assert "Количество возвратных остатков: 1" in response.text
	assert "Площадь возвратных остатков: 0.596 м²" in response.text
	assert "КИМ с учётом возвратных остатков: 75.60%" in response.text
	assert "1000 × 596" in response.text
	assert "596 × 400" not in response.text


def test_manual_form_post_passes_edges_to_svg_and_consumption() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual",
		data={
			"sheet_width_mm": "1000",
			"sheet_height_mm": "1000",
			"sheet_quantity": "1",
			"kerf_width_mm": "4",
			"margin_left_mm": "0",
			"margin_top_mm": "0",
			"margin_right_mm": "0",
			"margin_bottom_mm": "0",
			"parts_text": (
				"A1; Фасад; 300; 800; 1; "
				"1|0,5|10|ABS белая; "
				"1|0,5|0|ABS белая; "
				"2|0|20|ABS графит; "
				"1|0,5|5|ABS белая"
			),
		},
	)

	assert response.status_code == 200
	assert "Длина кромки: 2.200 м" in response.text
	assert "Длина кромки со свесом: 2.235 м" in response.text
	assert "Отрезов кромки: 4" in response.text
	assert "ABS белая" in response.text
	assert "ABS графит" in response.text
	assert 'data-logical-side="L1"' in response.text
	assert 'data-trimming-allowance-mm="0.5"' in response.text


def test_manual_form_post_returns_input_errors() -> None:
	client = TestClient(create_app())

	response = client.post(
		"/manual",
		data={
			"sheet_width_mm": "bad",
			"sheet_height_mm": "800",
			"sheet_quantity": "1",
			"kerf_width_mm": "4",
			"margin_left_mm": "0",
			"margin_top_mm": "0",
			"margin_right_mm": "0",
			"margin_bottom_mm": "0",
			"parts_text": "A1; Полка; 400; 300",
		},
	)

	assert response.status_code == 200
	assert "Ошибки ввода" in response.text
	assert "Ширина листа" in response.text
	assert "Строка 1" in response.text
	assert 'download="raskroi-report.txt"' not in response.text


def _make_xlsx(headers: list[object], rows: list[list[object]]) -> bytes:
	workbook = Workbook()
	worksheet = workbook.active
	worksheet.append(headers)
	for row in rows:
		worksheet.append(row)

	buffer = BytesIO()
	workbook.save(buffer)
	return buffer.getvalue()
