from fastapi.testclient import TestClient

from cutting_app.app.web import sample_preview
from cutting_app.app.web.app import create_app


def test_preview_page_displays_svg_and_messages() -> None:
	client = TestClient(create_app())

	response = client.get("/")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "<svg" in response.text
	assert "Скачать SVG" in response.text
	assert "DETAIL_DOES_NOT_FIT" in response.text


def test_svg_download_returns_svg_file() -> None:
	client = TestClient(create_app())

	response = client.get("/preview.svg")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("image/svg+xml")
	assert response.headers["content-disposition"] == 'attachment; filename="cutting-preview.svg"'
	assert "<svg" in response.text


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

	preview = sample_preview.build_sample_svg_preview()

	assert preview.svg == "<svg>fake</svg>"
	assert calls["result"] is preview.result
	assert calls["issues"] == preview.issues