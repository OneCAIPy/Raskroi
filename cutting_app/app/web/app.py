from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

from cutting_app.app.web.sample_preview import WebSvgPreview, build_sample_svg_preview


def create_app() -> FastAPI:
	app = FastAPI(title="Гильотинный раскрой Nanxing")

	@app.get("/", response_class=HTMLResponse)
	def show_svg_preview() -> HTMLResponse:
		preview = build_sample_svg_preview()
		return HTMLResponse(content=_render_preview_page(preview))

	@app.get("/preview.svg")
	def download_svg() -> Response:
		preview = build_sample_svg_preview()
		return Response(
			content=preview.svg,
			media_type="image/svg+xml",
			headers={
				"Content-Disposition": 'attachment; filename="cutting-preview.svg"',
			},
		)

	return app


def _render_preview_page(preview: WebSvgPreview) -> str:
	return f"""<!doctype html>
<html lang="ru">
<head>
	<meta charset="utf-8">
	<title>Гильотинный раскрой Nanxing — SVG preview</title>
	<style>
		body {{
			margin: 0;
			font-family: Arial, sans-serif;
			background: #f5f5f5;
			color: #222;
		}}

		header {{
			padding: 16px 24px;
			background: #222;
			color: white;
		}}

		main {{
			padding: 24px;
		}}

		.panel {{
			margin-bottom: 18px;
			padding: 16px;
			background: white;
			border: 1px solid #ddd;
			border-radius: 8px;
		}}

		.actions {{
			margin-top: 12px;
		}}

		.actions a {{
			display: inline-block;
			padding: 8px 12px;
			background: #1f6feb;
			color: white;
			text-decoration: none;
			border-radius: 6px;
		}}

		.issue {{
			margin: 6px 0;
			padding: 8px 10px;
			border-radius: 6px;
		}}

		.issue.error {{
			background: #ffe6e6;
			border: 1px solid #ffb3b3;
		}}

		.issue.warning {{
			background: #fff6d6;
			border: 1px solid #ffe08a;
		}}

		.svg-wrapper {{
			overflow: auto;
			background: white;
			border: 1px solid #ddd;
			border-radius: 8px;
			padding: 12px;
		}}
	</style>
</head>
<body>
	<header>
		<h1>Гильотинный раскрой Nanxing</h1>
		<div>Минимальный просмотр SVG-карты раскроя</div>
	</header>
	<main>
		<section class="panel">
			<h2>Тестовый раскрой</h2>
			{_render_metrics(preview)}
			<div class="actions">
				<a href="/preview.svg" download>Скачать SVG</a>
			</div>
		</section>

		<section class="panel">
			<h2>Ошибки и предупреждения</h2>
			{_render_messages(preview)}
		</section>

		<section class="svg-wrapper">
			{preview.svg}
		</section>
	</main>
</body>
</html>"""


def _render_metrics(preview: WebSvgPreview) -> str:
	metrics = preview.result.metrics

	return f"""
	<ul>
		<li>Листов использовано: {metrics.sheet_count}</li>
		<li>Деталей размещено: {metrics.placed_part_count}</li>
		<li>Деталей не размещено: {metrics.unplaced_part_count}</li>
		<li>Эффективность: {metrics.efficiency_percent:.2f}%</li>
	</ul>
	"""


def _render_messages(preview: WebSvgPreview) -> str:
	parts: list[str] = []

	for issue in preview.issues:
		parts.append(
			_render_issue(
				level=issue.level.value,
				code=issue.code,
				message=issue.message,
				part_number=issue.part_number,
				sheet_name=issue.sheet_name,
			)
		)

	for unplaced_part in preview.result.unplaced_parts:
		parts.append(
			_render_issue(
				level="error",
				code=unplaced_part.reason_code,
				message=unplaced_part.reason,
				part_number=unplaced_part.part_number,
				sheet_name=None,
			)
		)

	if not parts:
		return "<p>Ошибок и предупреждений нет.</p>"

	return "\n".join(parts)


def _render_issue(
	level: str,
	code: str,
	message: str,
	part_number: str | None,
	sheet_name: str | None,
) -> str:
	location_parts = []

	if sheet_name:
		location_parts.append(f"лист: {escape(sheet_name)}")

	if part_number:
		location_parts.append(f"деталь: {escape(part_number)}")

	location = ""
	if location_parts:
		location = f" ({', '.join(location_parts)})"

	return (
		f'<div class="issue {escape(level)}">'
		f"<strong>{escape(level.upper())}: {escape(code)}</strong>"
		f"{location}<br>"
		f"{escape(message)}"
		f"</div>"
	)