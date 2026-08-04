from base64 import b64encode
from html import escape

from cutting_app.app.domain.return_remnant import ReturnRemnantProfile
from cutting_app.app.exporters.txt_report_exporter import export_cutting_result_to_txt
from cutting_app.app.importers.parts_table_importer import EditablePartRow
from cutting_app.app.importers.remnant_table_importer import EditableRemnantRow
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
		{_render_form(form, preview)}
		{_render_preview(preview)}
	</main>
	{_render_scripts()}
</body>
</html>"""


def _render_form(
	form: ManualCuttingFormData,
	preview: ManualCuttingPreview | None,
) -> str:
	return f"""
{_render_xlsx_import_form(form)}
{_render_calculation_form(form, preview)}"""


def _render_xlsx_import_form(form: ManualCuttingFormData) -> str:
	return f"""
<section class="import-panel">
	<h3>1. Загрузить таблицу деталей</h3>
	<form method="post" action="/manual/import-xlsx" enctype="multipart/form-data">
		<label>Файл Excel
			<input type="file" name="parts_xlsx" accept=".xlsx">
		</label>
		<button type="submit">Загрузить XLSX</button>
	</form>
	<p class="hint">Загружаются позиции, размеры, количество, ориентация и отметки «*» в L1/L2/W1/W2. После загрузки все строки можно исправить вручную.</p>
	{_render_import_summary(form)}
</section>"""


def _render_import_summary(form: ManualCuttingFormData) -> str:
	if not form.imported_file_name:
		return ""

	sheet = (
		f", лист: {escape(form.imported_sheet_name)}"
		if form.imported_sheet_name
		else ""
	)
	skipped = ""
	if form.imported_skipped_row_count not in ("", "0"):
		skipped = (
			f" Строк с «Кроить = Нет» пропущено: "
			f"{escape(form.imported_skipped_row_count)}."
		)
	return (
		f'<p class="import-success">Загружен файл: '
		f"{escape(form.imported_file_name)}{sheet}. "
		f"Позиций в таблице: {len(form.part_rows)}.{skipped}</p>"
	)


def _render_calculation_form(
	form: ManualCuttingFormData,
	preview: ManualCuttingPreview | None,
) -> str:
	return f"""
<form method="post" action="/manual" id="manual-cutting-form">
	<input type="hidden" name="imported_file_name" value="{escape(form.imported_file_name)}">
	<input type="hidden" name="imported_sheet_name" value="{escape(form.imported_sheet_name)}">
	<input type="hidden" name="imported_skipped_row_count" value="{escape(form.imported_skipped_row_count)}">
	<fieldset>
		<legend>2. Стандартные листы</legend>
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
		<legend>3. Дополнительные куски клиента</legend>
		<p class="hint">Куски используются раньше стандартных листов. Размеры указываются с учётом направления материала; ко всем кускам применяются те же отступы от краёв, что и к стандартному листу.</p>
		{_render_remnants_table(form, preview)}
		<button type="button" class="secondary" id="add-remnant-row">Добавить кусок</button>
		<button type="button" class="danger" id="clear-remnant-rows">Очистить куски</button>
	</fieldset>

	<fieldset>
		<legend>4. Рез</legend>
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
		<legend>5. Отступы от краёв листов и кусков, мм</legend>
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
		<legend>6. Возвратные остатки</legend>
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
		<legend>7. Детали</legend>
		<div class="input-mode-selector">
			<label class="radio-label">
				<input type="radio" name="parts_input_mode" value="table"{_checked(form.parts_input_mode == "table")}>
				Редактируемая таблица
			</label>
			<label class="radio-label">
				<input type="radio" name="parts_input_mode" value="text"{_checked(form.parts_input_mode == "text")}>
				Текстовый ввод
			</label>
		</div>

		<section data-input-mode-panel="table">
			<h3>Общие параметры отмеченной кромки</h3>
			<label>Толщина кромки, мм
				<input name="edge_thickness_mm" value="{escape(form.edge_thickness_mm)}" inputmode="decimal">
			</label>
			<label>Прифуговка на сторону, мм
				<input name="edge_trimming_allowance_mm" value="{escape(form.edge_trimming_allowance_mm)}" inputmode="decimal">
			</label>
			<label>Материал кромки, необязательно
				<input name="edge_material_name" value="{escape(form.edge_material_name)}">
			</label>
			<p class="hint">Эти значения применяются только к сторонам, отмеченным галочками L1/L2/W1/W2. L и W — первый и второй размеры детали, а не обязательно длинная и короткая стороны.</p>
			{_render_parts_table(form, preview)}
			<button type="button" class="secondary" id="add-part-row">Добавить строку</button>
			<button type="button" class="danger" id="clear-part-rows">Очистить таблицу</button>
		</section>

		<details data-input-mode-panel="text"{_details_open(form.parts_input_mode == "text")}>
			<summary>Быстрый текстовый ввод</summary>
			<p class="hint">Старый формат: номер; название; L; W; количество</p>
			<p class="hint">Расширенный формат: номер; название; L; W; количество; L1; L2; W1; W2</p>
			<p class="hint">Кромка стороны: толщина|прифуговка|свес|материал. Пустое поле или «-» означает отсутствие кромки. Неуказанные прифуговка и свес равны нулю, материал можно не указывать.</p>
			<textarea name="parts_text" rows="10">{escape(form.parts_text)}</textarea>
		</details>
	</fieldset>

	<button type="submit">Рассчитать</button>
</form>"""


def _render_parts_table(
	form: ManualCuttingFormData,
	preview: ManualCuttingPreview | None,
) -> str:
	error_rows = set(preview.row_error_numbers if preview is not None else ())
	rows = form.part_rows or (EditablePartRow(),)
	body = "".join(
		_render_part_row(
			row,
			index=index,
			has_error=index + 1 in error_rows,
		)
		for index, row in enumerate(rows)
	)
	template_row = _render_part_row(
		EditablePartRow(),
		index=0,
		has_error=False,
	)
	return f"""
<div class="parts-table-wrapper">
	<table class="parts-table" id="parts-table">
		<thead>
			<tr>
				<th>№</th>
				<th>Позиция</th>
				<th>Наименование</th>
				<th>L, мм</th>
				<th>W, мм</th>
				<th>Кол-во</th>
				<th>Поворот</th>
				<th>L1</th>
				<th>L2</th>
				<th>W1</th>
				<th>W2</th>
				<th>Действия</th>
			</tr>
		</thead>
		<tbody>{body}</tbody>
	</table>
</div>
<template id="part-row-template">{template_row}</template>"""


def _render_remnants_table(
	form: ManualCuttingFormData,
	preview: ManualCuttingPreview | None,
) -> str:
	error_rows = set(
		preview.remnant_row_error_numbers
		if preview is not None
		else ()
	)
	rows = form.remnant_rows or (EditableRemnantRow(quantity="1"),)
	body = "".join(
		_render_remnant_row(
			row,
			index=index,
			has_error=index + 1 in error_rows,
		)
		for index, row in enumerate(rows)
	)
	template_row = _render_remnant_row(
		EditableRemnantRow(quantity="1"),
		index=0,
		has_error=False,
	)
	return f"""
<div class="remnants-table-wrapper">
	<table class="remnants-table" id="remnants-table">
		<thead>
			<tr>
				<th>№</th>
				<th>Ширина, мм</th>
				<th>Высота, мм</th>
				<th>Количество</th>
				<th>Действия</th>
			</tr>
		</thead>
		<tbody>{body}</tbody>
	</table>
</div>
<template id="remnant-row-template">{template_row}</template>"""


def _render_remnant_row(
	row: EditableRemnantRow,
	*,
	index: int,
	has_error: bool,
) -> str:
	row_class = ' class="row-error"' if has_error else ""
	return f"""
<tr{row_class}>
	<td class="remnant-row-number">{index + 1}</td>
	<td><input name="remnant_{index}_width_mm" value="{escape(row.width_mm)}" inputmode="decimal" aria-label="Ширина дополнительного куска"></td>
	<td><input name="remnant_{index}_height_mm" value="{escape(row.height_mm)}" inputmode="decimal" aria-label="Высота дополнительного куска"></td>
	<td><input name="remnant_{index}_quantity" value="{escape(row.quantity)}" inputmode="numeric" aria-label="Количество дополнительных кусков"></td>
	<td class="row-actions">
		<button type="button" class="secondary compact" data-remnant-action="duplicate">Дублировать</button>
		<button type="button" class="danger compact" data-remnant-action="delete">Удалить</button>
	</td>
</tr>"""


def _render_part_row(
	row: EditablePartRow,
	*,
	index: int,
	has_error: bool,
) -> str:
	row_class = ' class="row-error"' if has_error else ""
	return f"""
<tr{row_class}>
	<td class="row-number">{index + 1}</td>
	<td><input name="part_{index}_number" value="{escape(row.number)}" aria-label="Позиция"></td>
	<td><input name="part_{index}_name" value="{escape(row.name)}" aria-label="Наименование"></td>
	<td><input name="part_{index}_l_mm" value="{escape(row.l_mm)}" inputmode="decimal" aria-label="L"></td>
	<td><input name="part_{index}_w_mm" value="{escape(row.w_mm)}" inputmode="decimal" aria-label="W"></td>
	<td><input name="part_{index}_quantity" value="{escape(row.quantity)}" inputmode="numeric" aria-label="Количество"></td>
	<td class="checkbox-cell"><input type="checkbox" name="part_{index}_rotation_allowed"{_checked(row.rotation_allowed)} aria-label="Разрешить поворот"></td>
	<td class="checkbox-cell"><input type="checkbox" name="part_{index}_L1"{_checked(row.L1)} aria-label="Кромка L1"></td>
	<td class="checkbox-cell"><input type="checkbox" name="part_{index}_L2"{_checked(row.L2)} aria-label="Кромка L2"></td>
	<td class="checkbox-cell"><input type="checkbox" name="part_{index}_W1"{_checked(row.W1)} aria-label="Кромка W1"></td>
	<td class="checkbox-cell"><input type="checkbox" name="part_{index}_W2"{_checked(row.W2)} aria-label="Кромка W2"></td>
	<td class="row-actions">
		<button type="button" class="secondary compact" data-row-action="duplicate">Дублировать</button>
		<button type="button" class="danger compact" data-row-action="delete">Удалить</button>
	</td>
</tr>"""


def _selected(value: str, option: str) -> str:
	if value == option:
		return " selected"
	return ""


def _checked(value: bool) -> str:
	return " checked" if value else ""


def _details_open(value: bool) -> str:
	return " open" if value else ""


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
	{_render_txt_download_link(preview)}
	{_render_metrics(preview)}
	<h3>Ошибки и предупреждения</h3>
	{_render_issues(preview)}
	{preview.svg}
</section>"""


def _render_error_items(errors: list[str]) -> str:
	return "".join(f"<li>{escape(error)}</li>" for error in errors)


def _render_txt_download_link(preview: ManualCuttingPreview) -> str:
	if preview.result is None:
		return ""

	report_bytes = export_cutting_result_to_txt(preview.result).encode("utf-8")
	report_base64 = b64encode(report_bytes).decode("ascii")
	return (
		'<a class="button-link secondary download-report" '
		f'href="data:text/plain;charset=utf-8;base64,{report_base64}" '
		'download="raskroi-report.txt">Скачать отчёт TXT</a>'
	)


def _render_metrics(preview: ManualCuttingPreview) -> str:
	if preview.result is None:
		return ""

	metrics = preview.result.metrics
	edge_consumption = preview.result.edge_consumption
	production_length_item = _render_production_length_item(preview)
	production_count_items = _render_production_count_items(preview)
	return_remnant_profile_item = _render_return_remnant_profile_item(preview)
	return f"""
<ul>
	<li>Количество плит материала: {metrics.standard_sheet_count}</li>
	<li>Количество использованных дополнительных кусков: {metrics.input_remnant_count}</li>
	<li>КИМ: {metrics.material_utilization_percent:.2f}%</li>
	<li>КИМ с учётом возвратных остатков: {metrics.material_utilization_with_return_remnants_percent:.2f}%</li>
	<li>Площадь использованных плит и дополнительных кусков: {metrics.sheet_area_mm2 / 1_000_000:.3f} м²</li>
	<li>Площадь панелей: {metrics.placed_area_mm2 / 1_000_000:.3f} м²</li>
	<li>Площадь возвратных остатков: {metrics.return_remnant_area_mm2 / 1_000_000:.3f} м²</li>
	<li>Заполнение рабочей области: {metrics.working_area_efficiency_percent:.2f}%</li>
	{production_length_item}
</ul>
<h3>Облицовка</h3>
<ul>
	<li>Длина кромки: {edge_consumption.base_length_mm / 1000:.3f} м</li>
	<li>Длина кромки со свесом: {edge_consumption.total_length_mm / 1000:.3f} м</li>
	<li>Отрезов кромки: {edge_consumption.segment_count}</li>
</ul>
{_render_edge_material_consumption(preview)}
<ul>
	<li>Количество карт раскроя: {metrics.sheet_count}</li>
	<li>Количество панелей: {metrics.placed_part_count}</li>
	<li>Количество неразмещённых панелей: {metrics.unplaced_part_count}</li>
	<li>Количество возвратных остатков: {metrics.return_remnant_count}</li>
	{production_count_items}
	{return_remnant_profile_item}
</ul>
{_render_return_remnants(preview)}"""


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


def _render_production_length_item(preview: ManualCuttingPreview) -> str:
	if preview.result is None or preview.result.optimization is None:
		return ""

	score = preview.result.optimization.score
	return f"<li>Длина резов (проходов): {score.cut_length_mm / 1000:.4f} м</li>"


def _render_production_count_items(preview: ManualCuttingPreview) -> str:
	if preview.result is None or preview.result.optimization is None:
		return ""

	score = preview.result.optimization.score
	return f"""
	<li>Количество поворотов полос: {score.strip_turn_count}</li>
	<li>Количество установок размеров: {score.size_setting_count}</li>
	<li>Количество резов (проходов): {score.pass_count}</li>"""


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


def _render_scripts() -> str:
	return """
<script>
(() => {
	const form = document.getElementById("manual-cutting-form");
	const table = document.getElementById("parts-table");
	const template = document.getElementById("part-row-template");
	const addButton = document.getElementById("add-part-row");
	const clearButton = document.getElementById("clear-part-rows");
	const remnantsTable = document.getElementById("remnants-table");
	const remnantTemplate = document.getElementById("remnant-row-template");
	const addRemnantButton = document.getElementById("add-remnant-row");
	const clearRemnantButton = document.getElementById("clear-remnant-rows");
	if (
		!form || !table || !template || !addButton || !clearButton
		|| !remnantsTable || !remnantTemplate || !addRemnantButton
		|| !clearRemnantButton
	) {
		return;
	}

	const partsTableBody = table.querySelector("tbody");
	const remnantsTableBody = remnantsTable.querySelector("tbody");

	function renumberPartRows() {
		const rows = Array.from(partsTableBody.querySelectorAll("tr"));
		rows.forEach((row, index) => {
			const numberCell = row.querySelector(".row-number");
			if (numberCell) {
				numberCell.textContent = String(index + 1);
			}
			row.querySelectorAll("[name]").forEach((input) => {
				input.name = input.name.replace(/^part_\\d+_/, `part_${index}_`);
			});
		});
	}

	function renumberRemnantRows() {
		const rows = Array.from(remnantsTableBody.querySelectorAll("tr"));
		rows.forEach((row, index) => {
			const numberCell = row.querySelector(".remnant-row-number");
			if (numberCell) {
				numberCell.textContent = String(index + 1);
			}
			row.querySelectorAll("[name]").forEach((input) => {
				input.name = input.name.replace(/^remnant_\\d+_/, `remnant_${index}_`);
			});
		});
	}

	function blankRow() {
		const row = template.content.firstElementChild.cloneNode(true);
		row.classList.remove("row-error");
		return row;
	}

	function blankRemnantRow() {
		const row = remnantTemplate.content.firstElementChild.cloneNode(true);
		row.classList.remove("row-error");
		return row;
	}

	function clearRow(row) {
		row.classList.remove("row-error");
		row.querySelectorAll("input").forEach((input) => {
			if (input.type === "checkbox") {
				input.checked = input.name.endsWith("rotation_allowed");
			} else {
				input.value = "";
			}
		});
	}

	function clearRemnantRow(row) {
		row.classList.remove("row-error");
		row.querySelectorAll("input").forEach((input) => {
			input.value = input.name.endsWith("quantity") ? "1" : "";
		});
	}

	addButton.addEventListener("click", () => {
		partsTableBody.appendChild(blankRow());
		renumberPartRows();
	});
	clearButton.addEventListener("click", () => {
		partsTableBody.replaceChildren(blankRow());
		renumberPartRows();
	});

	partsTableBody.addEventListener("click", (event) => {
		const button = event.target.closest("button[data-row-action]");
		if (!button) {
			return;
		}
		const row = button.closest("tr");
		if (button.dataset.rowAction === "duplicate") {
			const copy = row.cloneNode(true);
			copy.classList.remove("row-error");
			row.after(copy);
		} else if (button.dataset.rowAction === "delete") {
			if (partsTableBody.querySelectorAll("tr").length === 1) {
				clearRow(row);
			} else {
				row.remove();
			}
		}
		renumberPartRows();
	});

	addRemnantButton.addEventListener("click", () => {
		remnantsTableBody.appendChild(blankRemnantRow());
		renumberRemnantRows();
	});
	clearRemnantButton.addEventListener("click", () => {
		remnantsTableBody.replaceChildren(blankRemnantRow());
		renumberRemnantRows();
	});

	remnantsTableBody.addEventListener("click", (event) => {
		const button = event.target.closest("button[data-remnant-action]");
		if (!button) {
			return;
		}
		const row = button.closest("tr");
		if (button.dataset.remnantAction === "duplicate") {
			const copy = row.cloneNode(true);
			copy.classList.remove("row-error");
			row.after(copy);
		} else if (button.dataset.remnantAction === "delete") {
			if (remnantsTableBody.querySelectorAll("tr").length === 1) {
				clearRemnantRow(row);
			} else {
				row.remove();
			}
		}
		renumberRemnantRows();
	});

	function updateInputMode() {
		const selected = form.querySelector('input[name="parts_input_mode"]:checked');
		if (!selected) {
			return;
		}
		form.querySelectorAll("[data-input-mode-panel]").forEach((panel) => {
			panel.hidden = panel.dataset.inputModePanel !== selected.value;
		});
	}

	form.querySelectorAll('input[name="parts_input_mode"]').forEach((radio) => {
		radio.addEventListener("change", updateInputMode);
	});
	form.addEventListener("submit", () => {
		renumberPartRows();
		renumberRemnantRows();
	});
	renumberPartRows();
	renumberRemnantRows();
	updateInputMode();
})();
</script>"""


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
		max-width: 1400px;
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
	input[type="checkbox"],
	input[type="radio"],
	input[type="file"] {
		width: auto;
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
		background: #1f6feb;
		color: #fff;
	}
	button.secondary {
		background: #e8edf3;
		color: #222;
	}
	button.danger {
		background: #fbe2e2;
		color: #8a1c1c;
	}
	button.compact {
		padding: 6px 9px;
		font-size: 12px;
	}
	.button-link {
		display: inline-block;
		padding: 10px 18px;
		border-radius: 8px;
		font-weight: 700;
		text-decoration: none;
	}
	.button-link.secondary {
		background: #e8edf3;
		color: #222;
	}
	.import-panel {
		margin: 16px 0;
		padding: 16px;
		border: 1px solid #b9cce8;
		border-radius: 8px;
		background: #f5f9ff;
	}
	.import-panel h3 {
		margin-top: 0;
	}
	.import-success {
		padding: 10px 12px;
		border-radius: 6px;
		background: #e8f6ea;
		color: #195c25;
		font-weight: 600;
	}
	.input-mode-selector {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
		margin: 8px 0 14px;
	}
	label.radio-label {
		display: inline-flex;
		flex-direction: row;
		align-items: center;
		gap: 7px;
		margin: 0;
	}
	.parts-table-wrapper {
		overflow-x: auto;
		margin: 12px 0;
	}
	.remnants-table-wrapper {
		overflow-x: auto;
		margin: 12px 0;
	}
	.remnants-table {
		margin: 0;
	}
	.remnants-table input {
		box-sizing: border-box;
		width: 130px;
		padding: 6px;
	}
	.parts-table {
		min-width: 1160px;
		margin: 0;
	}
	.parts-table th,
	.parts-table td {
		padding: 5px;
		vertical-align: middle;
	}
	.parts-table input:not([type="checkbox"]) {
		box-sizing: border-box;
		width: 96px;
		padding: 6px;
	}
	.parts-table td:nth-child(3) input {
		width: 180px;
	}
	.checkbox-cell {
		text-align: center;
	}
	.row-actions {
		white-space: nowrap;
	}
	.row-error td {
		background: #fff0f0;
	}
	.row-error input {
		border-color: #c62828;
	}
	details {
		margin-top: 16px;
		padding: 12px;
		border: 1px solid #ddd;
		border-radius: 6px;
	}
	details summary {
		cursor: pointer;
		font-weight: 700;
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
	.download-report {
		margin-bottom: 8px;
	}
	svg {
		max-width: 100%;
		height: auto;
		border: 1px solid #ddd;
		background: #fff;
	}
</style>"""
