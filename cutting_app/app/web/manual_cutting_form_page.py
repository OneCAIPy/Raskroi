from html import escape

from cutting_app.app.web.manual_cutting_form import ManualCuttingFormData, ManualCuttingPreview


def render_manual_cutting_form_page(
	form: ManualCuttingFormData,
	preview: ManualCuttingPreview | None = None,
) -> str:
	return f"""<!doctype html>
<html lang="ru">
<head>
	<meta charset="utf-8">
	<title>Ручной ввод раскроя</title>
	{_render_styles()}
</head>
<body>
	<main>
		<h1>Гильотинный раскрой Nanxing</h1>
		<p><a href="/">← К demo-заказам</a></p>
		<h2>Ручной ввод раскроя</h2>
		{_render_form(form)}
		{_render_preview(preview)}
	</main>
</body>
</html>"""


def _render_form(form: ManualCuttingFormData) -> str:
	return f"""
<form method="post" action="/manual">
	<fieldset>
		<legend>Лист</legend>
		<label>Ширина, мм
			<input name="sheet_width_mm" value="{escape(form.sheet_width_mm)}" inputmode="decimal">
		</label>
		<label>Высота, мм
			<input name="sheet_height_mm" value="{escape(form.sheet_height_mm)}" inputmode="decimal">
		</label>
		<label>Количество листов
			<input name="sheet_quantity" value="{escape(form.sheet_quantity)}" inputmode="numeric">
		</label>
	</fieldset>

	<fieldset>
		<legend>Рез</legend>
		<label>Ширина пропила, мм
			<input name="kerf_width_mm" value="{escape(form.kerf_width_mm)}" inputmode="decimal">
		</label>
	</fieldset>

	<fieldset>
		<legend>Отступы от краёв листа, мм</legend>
		<label>Слева
			<input name="margin_left_mm" value="{escape(form.margin_left_mm)}" inputmode="decimal">
		</label>
		<label>Сверху
			<input name="margin_top_mm" value="{escape(form.margin_top_mm)}" inputmode="decimal">
		</label>
		<label>Справа
			<input name="margin_right_mm" value="{escape(form.margin_right_mm)}" inputmode="decimal">
		</label>
		<label>Снизу
			<input name="margin_bottom_mm" value="{escape(form.margin_bottom_mm)}" inputmode="decimal">
		</label>
	</fieldset>

	<fieldset>
		<legend>Детали</legend>
		<p class="hint">Формат строки: номер; название; L; W; количество</p>
		<textarea name="parts_text" rows="10">{escape(form.parts_text)}</textarea>
	</fieldset>

	<button type="submit">Рассчитать</button>
</form>"""


def _render_preview(preview: ManualCuttingPreview | None) -> str:
	if preview is None:
		return ""

	if preview.input_errors:
		return f"""
<section class="errors">
	<h2>Ошибки ввода</h2>
	<ul>{_render_error_items(preview.input_errors)}</ul>
</section>"""

	if preview.result is None or preview.svg is None:
		return ""

	return f"""
<section class="result">
	<h2>Результат</h2>
	{_render_metrics(preview)}
	<h3>Ошибки и предупреждения</h3>
	{_render_issues(preview)}
	{preview.svg}
</section>"""


def _render_error_items(errors: list[str]) -> str:
	return "".join(f"<li>{escape(error)}</li>" for error in errors)


def _render_metrics(preview: ManualCuttingPreview) -> str:
	if preview.result is None:
		return ""

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
</ul>"""


def _render_issues(preview: ManualCuttingPreview) -> str:
	parts: list[str] = []
	for issue in preview.issues:
		parts.append(f"<li>{escape(issue.level.value.upper())}: {escape(issue.code)} — {escape(issue.message)}</li>")

	if preview.result is not None:
		for unplaced_part in preview.result.unplaced_parts:
			parts.append(
				f"<li>ERROR: {escape(unplaced_part.reason_code)} — "
				f"{escape(unplaced_part.part_number)}: {escape(unplaced_part.reason)}</li>"
			)

	if not parts:
		return "<p>Ошибок и предупреждений нет.</p>"

	return f"<ul>{''.join(parts)}</ul>"


def _render_styles() -> str:
	return """
<style>
	body {
		font-family: Arial, sans-serif;
		margin: 24px;
		background: #f7f7f7;
		color: #222;
	}
	main {
		max-width: 1180px;
		margin: 0 auto;
		background: #fff;
		padding: 24px;
		border-radius: 12px;
		box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
	}
	fieldset {
		margin: 16px 0;
		padding: 16px;
		border: 1px solid #ddd;
		border-radius: 8px;
	}
	label {
		display: inline-flex;
		flex-direction: column;
		gap: 4px;
		margin: 8px 16px 8px 0;
		font-weight: 600;
	}
	input {
		width: 140px;
		padding: 8px;
		border: 1px solid #bbb;
		border-radius: 6px;
	}
	textarea {
		box-sizing: border-box;
		width: 100%;
		padding: 12px;
		border: 1px solid #bbb;
		border-radius: 6px;
		font-family: Consolas, monospace;
	}
	button {
		padding: 10px 18px;
		border: 0;
		border-radius: 8px;
		font-weight: 700;
		cursor: pointer;
	}
	.hint {
		color: #666;
	}
	.errors {
		margin-top: 24px;
		padding: 16px;
		border: 1px solid #e6a0a0;
		border-radius: 8px;
		background: #fff2f2;
	}
	.result {
		margin-top: 24px;
	}
	svg {
		max-width: 100%;
		height: auto;
		border: 1px solid #ddd;
		background: #fff;
	}
</style>"""
