from fastapi.testclient import TestClient

from cutting_app.app.web import sample_preview
from cutting_app.app.web.app import create_app


def test_index_page_lists_demo_orders() -> None:
	client = TestClient(create_app())

	response = client.get("/")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "Простой раскрой без ошибок" in response.text
	assert 'href="/preview/simple"' in response.text
	assert 'href="/preview/cabinet"' in response.text


def test_preview_page_displays_selected_svg_and_messages() -> None:
	client = TestClient(create_app())

	response = client.get("/preview/error")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "Тестовый раскрой с неразмещённой деталью" in response.text
	assert "<svg" in response.text
	assert "Скачать SVG" in response.text
	assert 'href="/preview/error/svg"' in response.text
	assert "DETAIL_DOES_NOT_FIT" in response.text


def test_preview_page_without_errors_displays_empty_message() -> None:
	client = TestClient(create_app())

	response = client.get("/preview/simple")

	assert response.status_code == 200
	assert "<svg" in response.text
	assert "Ошибок и предупреждений нет." in response.text


def test_svg_download_returns_selected_svg_file() -> None:
	client = TestClient(create_app())

	response = client.get("/preview/error/svg")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("image/svg+xml")
	assert response.headers["content-disposition"] == 'attachment; filename="cutting-preview-error.svg"'
	assert "<svg" in response.text


def test_unknown_preview_returns_404() -> None:
	client = TestClient(create_app())

	response = client.get("/preview/missing")

	assert response.status_code == 404


def test_sample_preview_uses_selected_demo_order() -> None:
	preview = sample_preview.build_sample_svg_preview("cabinet")

	assert preview.order_slug == "cabinet"
	assert preview.order_name == "Почти реальный корпусный заказ"
	assert preview.result.metrics.unplaced_part_count == 0


def test_sample_preview_uses_svg_exporter(monkeypatch) -> None:
	calls = {}

	def fake_export_cutting_result_to_svg(result, issues=None):
		calls["result"] = result
		calls["issues"] = issues
		return "<svg>fake</svg>"

	monkeypatch.setattr(
		sample_preview.svg_exporter,
		"export_cutting_result_to_svg",
		fake_export_cutting_result_to_svg,
	)

	preview = sample_preview.build_sample_svg_preview("simple")

	assert preview.svg == "<svg>fake</svg>"
	assert calls["result"] is preview.result
	assert calls["issues"] == preview.issues
