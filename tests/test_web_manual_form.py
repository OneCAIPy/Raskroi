from fastapi.testclient import TestClient

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
	assert "textarea" in response.text
	assert "номер; название; L; W; количество; L1; L2; W1; W2" in response.text
	assert "толщина|прифуговка|свес|материал" in response.text
	assert "Рассчитать" in response.text


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
	assert "КИМ по площади материала:" in response.text
	assert "Заполнение рабочей области:" in response.text
	assert "Длина кромки: 0.000 м" in response.text
	assert "Длина кромки со свесом: 0.000 м" in response.text
	assert "Отрезов кромки: 0" in response.text
	assert "Длина проходов:" in response.text
	assert "Количество проходов:" in response.text
	assert "Поворотов полос:" in response.text
	assert "Установок размеров:" in response.text
	assert "Возвратных остатков:" in response.text
	assert "Площадь возвратных остатков:" in response.text
	assert "КИМ с учётом возвратных остатков:" in response.text
	assert "Размер (длинная × короткая), мм" in response.text
	assert 'value="horizontal" selected' in response.text
	assert 'value="long" selected' in response.text
	assert "Профиль возвратного остатка: длинный остаток" in response.text
	assert "Эффективность:" not in response.text
	assert "<svg" in response.text
	assert "placed-part" in response.text


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
	assert "Возвратных остатков: 2" in response.text
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
	assert "Возвратных остатков: 1" in response.text
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
