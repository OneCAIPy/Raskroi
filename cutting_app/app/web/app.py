from html import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from cutting_app.app.examples.demo_cutting_orders import list_demo_cutting_orders
from cutting_app.app.web.sample_preview import WebSvgPreview, build_sample_svg_preview

from cutting_app.app.web.manual_cutting_form import (
	build_manual_cutting_preview,
	make_default_manual_cutting_form,
	manual_cutting_form_from_urlencoded_body,
)
from cutting_app.app.web.manual_cutting_form_page import render_manual_cutting_form_page


def create_app() -> FastAPI:
	app = FastAPI(title="Гильотинный раскрой Nanxing")

	@app.get("/", response_class=HTMLResponse)
	def show_demo_order_list() -> HTMLResponse:
		return HTMLResponse(content=_render_demo_order_list_page())

	@app.get("/preview/{order_slug}", response_class=HTMLResponse)
	def show_svg_preview(order_slug: str) -> HTMLResponse:
		preview = _build_preview_or_404(order_slug)
		return HTMLResponse(content=_render_preview_page(preview))

	@app.get("/preview/{order_slug}/svg")
	def download_svg(order_slug: str) -> Response:
		preview = _build_preview_or_404(order_slug)
		filename = f"cutting-preview-{preview.order_slug}.svg"

		return Response(
			content=preview.svg,
			media_type="image/svg+xml",
			headers={
				"Content-Disposition": f'attachment; filename="{filename}"',
			},
		)
	
	@app.get("/manual", response_class=HTMLResponse)
	def show_manual_cutting_form() -> HTMLResponse:
		return HTMLResponse(
			content=render_manual_cutting_form_page(make_default_manual_cutting_form())
		)

	@app.post("/manual", response_class=HTMLResponse)
	async def calculate_manual_cutting(request: Request) -> HTMLResponse:
		form = manual_cutting_form_from_urlencoded_body(await request.body())
		preview = build_manual_cutting_preview(form)
		return HTMLResponse(content=render_manual_cutting_form_page(form, preview))

	return app


def _build_preview_or_404(order_slug: str) -> WebSvgPreview:
	try:
		return build_sample_svg_preview(order_slug)
	except ValueError as error:
		raise HTTPException(status_code=404, detail="Demo cutting order not found") from error


def _render_demo_order_list_page() -> str:
	items = "\n".join(
		_render_demo_order_link(order.slug, order.name)
		for order in list_demo_cutting_orders()
	)

	return f"""<!doctype html>
<html lang="ru">
<head>
	<meta charset="utf-8">
	<title>Гильотинный раскрой Nanxing — demo-заказы</title>
	{_render_styles()}
</head>
<body>
	<header>
		<h1>Гильотинный раскрой Nanxing</h1>
		<div>Выбор demo-заказа для просмотра SVG</div>
	</header>
	<main>
		<section class="panel">
			<h2>Demo-заказы</h2>
			<p><a href="/manual">Ручной ввод раскроя</a></p>
			<p>Выбери сценарий, чтобы посмотреть карту раскроя и скачать SVG.</p>
			<div class="order-list">
				{items}
			</div>
		</section>
	</main>
</body>
</html>"""


def _render_demo_order_link(slug: str, name: str) -> str:
	return (
		f'<a class="order-card" href="/preview/{escape(slug)}">'
		f"<strong>{escape(name)}</strong>"
		f"<span>{escape(slug)}</span>"
		f"</a>"
	)


def _render_preview_page(preview: WebSvgPreview) -> str:
	return f"""<!doctype html>
<html lang="ru">
<head>
	<meta charset="utf-8">
	<title>{escape(preview.order_name)} — SVG preview</title>
	{_render_styles()}
</head>
<body>
	<header>
		<h1>Гильотинный раскрой Nanxing</h1>
		<div>Минимальный просмотр SVG-карты раскроя</div>
	</header>
	<main>
		<section class="panel">
			<a href="/">← К списку demo-заказов</a>
			<h2>{escape(preview.order_name)}</h2>
			{_render_metrics(preview)}
			<div class="actions">
				<a href="/preview/{escape(preview.order_slug)}/svg" download>Скачать SVG</a>
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


def _render_styles() -> str:
	return """<style>
		body {
			margin: 0;
			font-family: Arial, sans-serif;
			background: #f5f5f5;
			color: #222;
		}

		header {
			padding: 16px 24px;
			background: #222;
			color: white;
		}

		main {
			padding: 24px;
		}

		.panel {
			margin-bottom: 18px;
			padding: 16px;
			background: white;
			border: 1px solid #ddd;
			border-radius: 8px;
		}

		.actions {
			margin-top: 12px;
		}

		.actions a {
			display: inline-block;
			padding: 8px 12px;
			background: #1f6feb;
			color: white;
			text-decoration: none;
			border-radius: 6px;
		}

		.order-list {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
			gap: 12px;
		}

		.order-card {
			display: block;
			padding: 14px;
			color: #222;
			text-decoration: none;
			background: #fafafa;
			border: 1px solid #ddd;
			border-radius: 8px;
		}

		.order-card:hover {
			background: #eef5ff;
			border-color: #1f6feb;
		}

		.order-card span {
			display: block;
			margin-top: 6px;
			color: #666;
			font-size: 13px;
		}

		.issue {
			margin: 6px 0;
			padding: 8px 10px;
			border-radius: 6px;
		}

		.issue.error {
			background: #ffe6e6;
			border: 1px solid #ffb3b3;
		}

		.issue.warning {
			background: #fff6d6;
			border: 1px solid #ffe08a;
		}

		.svg-wrapper {
			overflow: auto;
			background: white;
			border: 1px solid #ddd;
			border-radius: 8px;
			padding: 12px;
		}
	</style>"""


def _render_metrics(preview: WebSvgPreview) -> str:
	metrics = preview.result.metrics
	edge_consumption = preview.result.edge_consumption

	return f"""
	<ul>
		<li>Листов использовано: {metrics.sheet_count}</li>
		<li>Деталей размещено: {metrics.placed_part_count}</li>
		<li>Деталей не размещено: {metrics.unplaced_part_count}</li>
		<li>КИМ по площади материала: {metrics.material_utilization_percent:.2f}%</li>
		<li>Заполнение рабочей области: {metrics.working_area_efficiency_percent:.2f}%</li>
		<li>Длина кромки: {edge_consumption.base_length_mm / 1000:.3f} м</li>
		<li>Длина кромки со свесом: {edge_consumption.total_length_mm / 1000:.3f} м</li>
		<li>Отрезов кромки: {edge_consumption.segment_count}</li>
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
