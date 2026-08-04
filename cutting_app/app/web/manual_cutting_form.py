from dataclasses import dataclass
import re
from urllib.parse import parse_qs

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cut_tree import CutDirection
from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.return_remnant import (
	ReturnRemnantProfile,
	ReturnRemnantSettings,
)
from cutting_app.app.domain.result_issue import ResultIssue
from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.exporters import svg_exporter
from cutting_app.app.importers.manual_parts_text_importer import parse_manual_parts_text
from cutting_app.app.importers.parts_table_importer import (
	EditablePartRow,
	parse_editable_part_rows,
)
from cutting_app.app.importers.remnant_table_importer import (
	EditableRemnantRow,
	parse_editable_remnant_rows,
)
from cutting_app.app.services.cutting_result_validator import validate_cutting_result
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting


DEFAULT_PARTS_TEXT = """A1; Боковина; 720; 500; 2
A2; Полка; 680; 300; 3
A3; Цоколь; 680; 100; 2"""

DEFAULT_PART_ROWS = (
	EditablePartRow(
		number="A1",
		name="Боковина",
		l_mm="720",
		w_mm="500",
		quantity="2",
	),
	EditablePartRow(
		number="A2",
		name="Полка",
		l_mm="680",
		w_mm="300",
		quantity="3",
	),
	EditablePartRow(
		number="A3",
		name="Цоколь",
		l_mm="680",
		w_mm="100",
		quantity="2",
	),
)

_PART_ROW_FIELD_PATTERN = re.compile(r"^part_(\d+)_")
_REMNANT_ROW_FIELD_PATTERN = re.compile(r"^remnant_(\d+)_")


@dataclass(frozen=True)
class ManualCuttingFormData:
	sheet_width_mm: str
	sheet_height_mm: str
	sheet_quantity: str
	kerf_width_mm: str
	margin_left_mm: str
	margin_top_mm: str
	margin_right_mm: str
	margin_bottom_mm: str
	parts_text: str
	initial_cut_direction: str = CutDirection.VERTICAL.value
	return_remnant_profile: str = ReturnRemnantProfile.MAX_USEFUL_AREA.value
	return_remnant_min_long_side_mm: str = "400"
	return_remnant_min_short_side_mm: str = "80"
	return_remnant_min_area_m2: str = "0.04"
	parts_input_mode: str = "table"
	edge_thickness_mm: str = "1"
	edge_trimming_allowance_mm: str = "0.5"
	edge_material_name: str = ""
	part_rows: tuple[EditablePartRow, ...] = ()
	remnant_rows: tuple[EditableRemnantRow, ...] = ()
	imported_file_name: str = ""
	imported_sheet_name: str = ""
	imported_skipped_row_count: str = "0"


@dataclass(frozen=True)
class ManualCuttingPreview:
	result: CuttingResult | None
	issues: list[ResultIssue]
	svg: str | None
	input_errors: list[str]
	row_error_numbers: tuple[int, ...] = ()
	remnant_row_error_numbers: tuple[int, ...] = ()


@dataclass(frozen=True)
class _ParsedManualForm:
	sheet_width_mm: float
	sheet_height_mm: float
	sheet_quantity: int
	kerf_width_mm: float
	initial_cut_direction: CutDirection
	margins: SheetMargins
	return_remnant_settings: ReturnRemnantSettings | None
	errors: list[str]


def make_default_manual_cutting_form() -> ManualCuttingFormData:
	return ManualCuttingFormData(
		sheet_width_mm="2800",
		sheet_height_mm="2070",
		sheet_quantity="100",
		kerf_width_mm="4,4",
		margin_left_mm="10",
		margin_top_mm="10",
		margin_right_mm="10",
		margin_bottom_mm="10",
		parts_text=DEFAULT_PARTS_TEXT,
		initial_cut_direction=CutDirection.VERTICAL.value,
		return_remnant_profile=ReturnRemnantProfile.MAX_USEFUL_AREA.value,
		return_remnant_min_long_side_mm="400",
		return_remnant_min_short_side_mm="80",
		return_remnant_min_area_m2="0.04",
		parts_input_mode="table",
		edge_thickness_mm="1",
		edge_trimming_allowance_mm="0.5",
		edge_material_name="",
		part_rows=DEFAULT_PART_ROWS,
		remnant_rows=(),
	)


def manual_cutting_form_from_urlencoded_body(body: bytes) -> ManualCuttingFormData:
	values = parse_qs(body.decode("utf-8"), keep_blank_values=True)
	default_form = make_default_manual_cutting_form()
	return ManualCuttingFormData(
		sheet_width_mm=_first(values, "sheet_width_mm", default_form.sheet_width_mm),
		sheet_height_mm=_first(values, "sheet_height_mm", default_form.sheet_height_mm),
		sheet_quantity=_first(values, "sheet_quantity", default_form.sheet_quantity),
		kerf_width_mm=_first(values, "kerf_width_mm", default_form.kerf_width_mm),
		margin_left_mm=_first(values, "margin_left_mm", default_form.margin_left_mm),
		margin_top_mm=_first(values, "margin_top_mm", default_form.margin_top_mm),
		margin_right_mm=_first(values, "margin_right_mm", default_form.margin_right_mm),
		margin_bottom_mm=_first(values, "margin_bottom_mm", default_form.margin_bottom_mm),
		parts_text=_first(values, "parts_text", default_form.parts_text),
		initial_cut_direction=_first(
			values,
			"initial_cut_direction",
			default_form.initial_cut_direction,
		),
		return_remnant_profile=_first(
			values,
			"return_remnant_profile",
			default_form.return_remnant_profile,
		),
		return_remnant_min_long_side_mm=_first(
			values,
			"return_remnant_min_long_side_mm",
			default_form.return_remnant_min_long_side_mm,
		),
		return_remnant_min_short_side_mm=_first(
			values,
			"return_remnant_min_short_side_mm",
			default_form.return_remnant_min_short_side_mm,
		),
		return_remnant_min_area_m2=_first(
			values,
			"return_remnant_min_area_m2",
			default_form.return_remnant_min_area_m2,
		),
		parts_input_mode=_first(
			values,
			"parts_input_mode",
			default_form.parts_input_mode,
		),
		edge_thickness_mm=_first(
			values,
			"edge_thickness_mm",
			default_form.edge_thickness_mm,
		),
		edge_trimming_allowance_mm=_first(
			values,
			"edge_trimming_allowance_mm",
			default_form.edge_trimming_allowance_mm,
		),
		edge_material_name=_first(
			values,
			"edge_material_name",
			default_form.edge_material_name,
		),
		part_rows=_parse_part_rows(values),
		remnant_rows=_parse_remnant_rows(values),
		imported_file_name=_first(values, "imported_file_name", ""),
		imported_sheet_name=_first(values, "imported_sheet_name", ""),
		imported_skipped_row_count=_first(
			values,
			"imported_skipped_row_count",
			"0",
		),
	)


def build_manual_cutting_preview(form: ManualCuttingFormData) -> ManualCuttingPreview:
	parsed_form = _parse_manual_form(form)
	input_errors = [*parsed_form.errors]
	row_error_numbers: tuple[int, ...] = ()
	remnant_row_error_numbers: tuple[int, ...] = ()
	parts = []
	remnant_result = parse_editable_remnant_rows(
		form.remnant_rows,
		margins=parsed_form.margins,
	)
	input_errors.extend(
		f"Дополнительный кусок {error.row_number}: {error.message}"
		for error in remnant_result.errors
	)
	remnant_row_error_numbers = tuple(
		error.row_number
		for error in remnant_result.errors
	)

	if form.parts_input_mode not in ("table", "text"):
		input_errors.append("Источник деталей: выбери таблицу или текстовый ввод.")

	use_table = form.parts_input_mode == "table" and bool(form.part_rows)
	if use_table:
		parts_result = parse_editable_part_rows(
			form.part_rows,
			edge_thickness_mm=form.edge_thickness_mm,
			edge_trimming_allowance_mm=form.edge_trimming_allowance_mm,
			edge_material_name=form.edge_material_name,
		)
		parts = parts_result.parts
		input_errors.extend(
			f"Строка таблицы {error.row_number}: {error.message}"
			for error in parts_result.errors
		)
		row_error_numbers = tuple(
			error.row_number
			for error in parts_result.errors
		)
	else:
		parts_result = parse_manual_parts_text(form.parts_text)
		parts = parts_result.parts
		input_errors.extend(
			f"Строка {error.line_number}: {error.message} Текст: {error.line_text}"
			for error in parts_result.errors
		)

	if not parts:
		input_errors.append("Добавь хотя бы одну корректную деталь.")

	if input_errors:
		return ManualCuttingPreview(
			result=None,
			issues=[],
			svg=None,
			input_errors=input_errors,
			row_error_numbers=row_error_numbers,
			remnant_row_error_numbers=remnant_row_error_numbers,
		)

	if parsed_form.return_remnant_settings is None:
		raise ValueError("Не удалось разобрать настройки возвратных остатков.")

	standard_sheet = SheetInput(
		name="Лист",
		width_mm=parsed_form.sheet_width_mm,
		height_mm=parsed_form.sheet_height_mm,
		quantity=parsed_form.sheet_quantity,
		margins=parsed_form.margins,
	)
	settings = CutSettings(
		kerf_width_mm=parsed_form.kerf_width_mm,
		initial_cut_direction=parsed_form.initial_cut_direction,
	)
	result = optimize_guillotine_cutting(
		parts=parts,
		sheets=[*remnant_result.sheets, standard_sheet],
		settings=settings,
		return_remnant_settings=parsed_form.return_remnant_settings,
	)
	issues = validate_cutting_result(result)
	svg = svg_exporter.export_cutting_result_to_svg(result, issues=issues)

	return ManualCuttingPreview(
		result=result,
		issues=issues,
		svg=svg,
		input_errors=[],
	)


def build_manual_cutting_rows_validation(
	form: ManualCuttingFormData,
	*,
	additional_errors: list[str] | None = None,
	additional_row_error_numbers: list[int] | None = None,
) -> ManualCuttingPreview:
	parts_result = parse_editable_part_rows(
		form.part_rows,
		edge_thickness_mm=form.edge_thickness_mm,
		edge_trimming_allowance_mm=form.edge_trimming_allowance_mm,
		edge_material_name=form.edge_material_name,
	)
	errors = [*(additional_errors or [])]
	errors.extend(
		f"Строка таблицы {error.row_number}: {error.message}"
		for error in parts_result.errors
	)
	if not form.part_rows and not errors:
		errors.append("В Excel не найдено ни одной строки деталей для раскроя.")

	row_error_numbers = {
		*(additional_row_error_numbers or []),
		*(error.row_number for error in parts_result.errors),
	}
	return ManualCuttingPreview(
		result=None,
		issues=[],
		svg=None,
		input_errors=errors,
		row_error_numbers=tuple(sorted(row_error_numbers)),
	)


def _parse_manual_form(form: ManualCuttingFormData) -> _ParsedManualForm:
	errors: list[str] = []

	sheet_width_mm = _parse_float(form.sheet_width_mm, "Ширина листа", errors, min_value=0, include_min=False)
	sheet_height_mm = _parse_float(form.sheet_height_mm, "Высота листа", errors, min_value=0, include_min=False)
	sheet_quantity = _parse_int(form.sheet_quantity, "Количество листов", errors, min_value=0, include_min=False)
	kerf_width_mm = _parse_float(form.kerf_width_mm, "Ширина пропила", errors, min_value=0, include_min=True)
	initial_cut_direction = _parse_initial_cut_direction(
		form.initial_cut_direction,
		errors,
	)
	margin_left_mm = _parse_float(form.margin_left_mm, "Отступ слева", errors, min_value=0, include_min=True)
	margin_top_mm = _parse_float(form.margin_top_mm, "Отступ сверху", errors, min_value=0, include_min=True)
	margin_right_mm = _parse_float(form.margin_right_mm, "Отступ справа", errors, min_value=0, include_min=True)
	margin_bottom_mm = _parse_float(form.margin_bottom_mm, "Отступ снизу", errors, min_value=0, include_min=True)
	return_remnant_min_long_side_mm = _parse_float(
		form.return_remnant_min_long_side_mm,
		"Минимальная длинная сторона возвратного остатка",
		errors,
		min_value=0,
		include_min=True,
	)
	return_remnant_min_short_side_mm = _parse_float(
		form.return_remnant_min_short_side_mm,
		"Минимальная короткая сторона возвратного остатка",
		errors,
		min_value=0,
		include_min=True,
	)
	return_remnant_min_area_m2 = _parse_float(
		form.return_remnant_min_area_m2,
		"Минимальная площадь возвратного остатка",
		errors,
		min_value=0,
		include_min=True,
	)
	return_remnant_profile = _parse_return_remnant_profile(
		form.return_remnant_profile,
		errors,
	)
	return_remnant_settings = _build_return_remnant_settings(
		min_long_side_mm=return_remnant_min_long_side_mm,
		min_short_side_mm=return_remnant_min_short_side_mm,
		min_area_m2=return_remnant_min_area_m2,
		value_profile=return_remnant_profile,
		errors=errors,
	)

	return _ParsedManualForm(
		sheet_width_mm=sheet_width_mm,
		sheet_height_mm=sheet_height_mm,
		sheet_quantity=sheet_quantity,
		kerf_width_mm=kerf_width_mm,
		initial_cut_direction=initial_cut_direction,
		margins=SheetMargins(
			left_mm=margin_left_mm,
			top_mm=margin_top_mm,
			right_mm=margin_right_mm,
			bottom_mm=margin_bottom_mm,
		),
		return_remnant_settings=return_remnant_settings,
		errors=errors,
	)


def _build_return_remnant_settings(
	*,
	min_long_side_mm: float,
	min_short_side_mm: float,
	min_area_m2: float,
	value_profile: ReturnRemnantProfile,
	errors: list[str],
) -> ReturnRemnantSettings | None:
	if min_long_side_mm < min_short_side_mm:
		errors.append(
			"Возвратный остаток: минимальная длинная сторона не может быть меньше короткой."
		)
		return None

	return ReturnRemnantSettings(
		min_long_side_mm=min_long_side_mm,
		min_short_side_mm=min_short_side_mm,
		min_area_mm2=min_area_m2 * 1_000_000,
		value_profile=value_profile,
	)


def _parse_initial_cut_direction(
	value: str,
	errors: list[str],
) -> CutDirection:
	try:
		return CutDirection(value.strip().lower())
	except ValueError:
		errors.append(
			"Первое направление резов: выбери вертикальное или горизонтальное."
		)
		return CutDirection.VERTICAL


def _parse_return_remnant_profile(
	value: str,
	errors: list[str],
) -> ReturnRemnantProfile:
	try:
		return ReturnRemnantProfile(value.strip().lower())
	except ValueError:
		errors.append(
			"Профиль возвратного остатка: выбери максимальную полезную площадь, длинный или компактный остаток."
		)
		return ReturnRemnantProfile.MAX_USEFUL_AREA


def _first(values: dict[str, list[str]], name: str, default: str) -> str:
	items = values.get(name)
	if not items:
		return default
	return items[0]


def _parse_part_rows(values: dict[str, list[str]]) -> tuple[EditablePartRow, ...]:
	row_indexes = sorted(
		{
			int(match.group(1))
			for name in values
			if (match := _PART_ROW_FIELD_PATTERN.match(name)) is not None
		}
	)
	return tuple(
		EditablePartRow(
			number=_first(values, f"part_{index}_number", ""),
			name=_first(values, f"part_{index}_name", ""),
			l_mm=_first(values, f"part_{index}_l_mm", ""),
			w_mm=_first(values, f"part_{index}_w_mm", ""),
			quantity=_first(values, f"part_{index}_quantity", ""),
			rotation_allowed=_is_checked(
				values,
				f"part_{index}_rotation_allowed",
			),
			L1=_is_checked(values, f"part_{index}_L1"),
			L2=_is_checked(values, f"part_{index}_L2"),
			W1=_is_checked(values, f"part_{index}_W1"),
			W2=_is_checked(values, f"part_{index}_W2"),
		)
		for index in row_indexes
	)


def _parse_remnant_rows(
	values: dict[str, list[str]],
) -> tuple[EditableRemnantRow, ...]:
	row_indexes = sorted(
		{
			int(match.group(1))
			for name in values
			if (match := _REMNANT_ROW_FIELD_PATTERN.match(name)) is not None
		}
	)
	return tuple(
		EditableRemnantRow(
			width_mm=_first(values, f"remnant_{index}_width_mm", ""),
			height_mm=_first(values, f"remnant_{index}_height_mm", ""),
			quantity=_first(values, f"remnant_{index}_quantity", ""),
		)
		for index in row_indexes
	)


def _is_checked(values: dict[str, list[str]], name: str) -> bool:
	items = values.get(name)
	if not items:
		return False
	return items[0].strip().lower() not in ("", "0", "false", "off", "нет")


def _parse_float(
	value: str,
	field_name: str,
	errors: list[str],
	*,
	min_value: float,
	include_min: bool,
) -> float:
	try:
		parsed = float(value.replace(",", "."))
	except ValueError:
		errors.append(f"{field_name}: должно быть число.")
		return 0.0

	if include_min and parsed < min_value:
		errors.append(f"{field_name}: должно быть не меньше {min_value}.")
		return 0.0

	if not include_min and parsed <= min_value:
		errors.append(f"{field_name}: должно быть больше {min_value}.")
		return 0.0

	return parsed


def _parse_int(
	value: str,
	field_name: str,
	errors: list[str],
	*,
	min_value: int,
	include_min: bool,
) -> int:
	try:
		parsed = int(value)
	except ValueError:
		errors.append(f"{field_name}: должно быть целое число.")
		return 0

	if include_min and parsed < min_value:
		errors.append(f"{field_name}: должно быть не меньше {min_value}.")
		return 0

	if not include_min and parsed <= min_value:
		errors.append(f"{field_name}: должно быть больше {min_value}.")
		return 0

	return parsed
