from fastapi.testclient import TestClient

from cutting_app.app.web.app import create_app


def test_manual_form_page_is_available() -> None:
	client = TestClient(create_app())

	response = client.get("/manual")

	assert response.status_code == 200
	assert "Ручной ввод раскроя" in response.text
	assert "textarea" in response.text
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
	assert "Эффективность:" not in response.text
	assert "<svg" in response.text
	assert "placed-part" in response.text


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
