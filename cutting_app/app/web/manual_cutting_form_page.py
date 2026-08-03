from html import escape

from cutting_app.app.domain.return_remnant import ReturnRemnantProfile
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
		<label>Первое направление при раскрое без разделительных резов
			<select name="initial_cut_direction">
				<option value="vertical"{_selected(form.initial_cut_direction, "vertical")}>Вертикальные проходы первыми</option>
				<option value="horizontal"{_selected(form.initial_cut_direction, "horizontal")}>Горизонтальные проходы первыми</option>
			</select>
		</label>
		<p class="hint">Используется, когда одна деталь точно занимает всю рабочую область, а порядок торцовок нельзя восстановить из дерева резов.</p>
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
		<legend>Возвратные остатки</legend>
		<label>Желаемый профиль остатка
			<select name="return_remnant_profile">
				<option value="max_useful_area"{_selected(form.return_remnant_profile, "max_useful_area")}>Максимальная полезная площадь</option>
				<option value="long"{_selected(form.return_remnant_profile, "long")}>Длинный остаток</option>
				<option value="compact"{_selected(form.return_remnant_profile, "compact")}>Компактный остаток</option>
			</select>
		</label>
		<label>Минимальная длинная сторона, мм
			<input name="return_remnant_min_long_side_mm" value="{escape(form.return_remnant_min_long_side_mm)}" inputmode="decimal">
		</label>
		<label>Минимальная короткая сторона, мм
			<input name="return_remnant_min_short_side_mm" value="{escape(form.return_remnant_min_short_side_mm)}" inputmode="decimal">
		</label>
		<label>Минимальная площадь, м²
			<input name="return_remnant_min_area_m2" value="{escape(form.return_remnant_min_area_m2)}" inputmode="decimal">
		</label>
		<p class="hint">Площадь сохраняет максимум полезного материала; длинный профиль ищет остаток с наибольшей длинной стороной; компактный — остаток с наибольшим вписываемым квадратом.</p>
		<p class="hint">По умолчанию используются пороги эталона БАЗИСа: 400 × 80 мм и 0,04 м². Учитываются только физически отделяемые прямоугольные листья дерева резов.</p>
	</fieldset>

	<fieldset>
		<legend>Детали</legend>
		<p class="hint">Старый формат: номер; название; L; W; количество</p>
		<p class="hint">Расширенный формат: номер; название; L; W; количество; L1; L2; W1; W2</p>
		<p class="hint">Кромка стороны: толщина|прифуговка|свес|материал. Пустое поле или «-» означает отсутствие кромки. Неуказанные прифуговка и свес равны нулю, материал можно не указывать.</p>
		<textarea name="parts_text" rows="10">{escape(form.parts_text)}</textarea>
	</fieldset>

	<button type="submit">Рассчитать</button>
</form>"""


def _selected(value: str, option: str) -> str:
	if value == option:
		return " selected"
	return ""


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
	production_items = _render_production_metric_items(preview)
	return_remnant_profile_item = _render_return_remnant_profile_item(preview)
	return f"""
<ul>
	<li>Листов использовано: {metrics.sheet_count}</li>
	<li>Деталей размещено: {metrics.placed_part_count}</li>
	<li>Деталей не размещено: {metrics.unplaced_part_count}</li>
	<li>КИМ по площади материала: {metrics.material_utilization_percent:.2f}%</li>
	<li>Возвратных остатков: {metrics.return_remnant_count}</li>
	<li>Площадь возвратных остатков: {metrics.return_remnant_area_mm2 / 1_000_000:.3f} м²</li>
	<li>КИМ с учётом возвратных остатков: {metrics.material_utilization_with_return_remnants_percent:.2f}%</li>
	{return_remnant_profile_item}
	<li>Заполнение рабочей области: {metrics.working_area_efficiency_percent:.2f}%</li>
	<li>Длина кромки: {edge_consumption.base_length_mm / 1000:.3f} м</li>
	<li>Длина кромки со свесом: {edge_consumption.total_length_mm / 1000:.3f} м</li>
	<li>Отрезов кромки: {edge_consumption.segment_count}</li>
	{production_items}
</ul>
{_render_return_remnants(preview)}
{_render_edge_material_consumption(preview)}"""


def _render_return_remnant_profile_item(preview: ManualCuttingPreview) -> str:
	if preview.result is None or preview.result.optimization is None:
		return ""

	profile = preview.result.optimization.score.return_remnant_profile
	labels = {
		ReturnRemnantProfile.MAX_USEFUL_AREA: "максимальная полезная площадь",
		ReturnRemnantProfile.LONG: "длинный остаток",
		ReturnRemnantProfile.COMPACT: "компактный остаток",
	}
	return f"<li>Профиль возвратного остатка: {labels[profile]}</li>"


def _render_production_metric_items(preview: ManualCuttingPreview) -> str:
	if preview.result is None or preview.result.optimization is None:
		return ""

	score = preview.result.optimization.score
	return f"""
	<li>Длина проходов: {score.cut_length_mm / 1000:.4f} м</li>
	<li>Количество проходов: {score.pass_count}</li>
	<li>Поворотов полос: {score.strip_turn_count}</li>
	<li>Установок размеров: {score.size_setting_count}</li>"""


def _render_edge_material_consumption(preview: ManualCuttingPreview) -> str:
	if preview.result is None or not preview.result.edge_consumption.by_material:
		return ""

	rows = "".join(
		f"""
	<tr>
		<td>{escape(item.material_name or "Не указан")}</td>
		<td>{item.thickness_mm:g}</td>
		<td>{item.segment_count}</td>
		<td>{item.base_length_mm / 1000:.3f}</td>
		<td>{item.overhang_length_mm / 1000:.3f}</td>
		<td>{item.total_length_mm / 1000:.3f}</td>
	</tr>"""
		for item in preview.result.edge_consumption.by_material
	)
	return f"""
<h3>Расход кромки по материалам</h3>
<table>
	<thead>
		<tr>
			<th>Материал</th>
			<th>Толщина, мм</th>
			<th>Отрезов</th>
			<th>Базовая длина, м</th>
			<th>Свес, м</th>
			<th>Всего, м</th>
		</tr>
	</thead>
	<tbody>{rows}</tbody>
</table>"""


def _render_return_remnants(preview: ManualCuttingPreview) -> str:
	if preview.result is None:
		return ""

	if not preview.result.return_remnants:
		return """
<h3>Возвратные остатки</h3>
<p>Остатков, проходящих заданные пороги, нет.</p>"""

	rows = "".join(
		f"""
	<tr>
		<td>{index}</td>
		<td>{escape(remnant.sheet_name)}</td>
		<td>{remnant.long_side_mm:g} × {remnant.short_side_mm:g}</td>
		<td>{remnant.area_mm2 / 1_000_000:.3f}</td>
	</tr>"""
		for index, remnant in enumerate(preview.result.return_remnants, start=1)
	)
	return f"""
<h3>Возвратные остатки</h3>
<table>
	<thead>
		<tr>
			<th>№</th>
			<th>Лист</th>
			<th>Размер (длинная × короткая), мм</th>
			<th>Площадь, м²</th>
		</tr>
	</thead>
	<tbody>{rows}</tbody>
</table>"""


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
	input,
	select {
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
	table {
		border-collapse: collapse;
		margin: 12px 0 20px;
	}
	th,
	td {
		padding: 7px 10px;
		border: 1px solid #ccc;
		text-align: left;
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
