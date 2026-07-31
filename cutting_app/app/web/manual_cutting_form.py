from dataclasses import dataclass
from urllib.parse import parse_qs

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cut_tree import CutDirection
from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.result_issue import ResultIssue
from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.exporters import svg_exporter
from cutting_app.app.importers.manual_parts_text_importer import parse_manual_parts_text
from cutting_app.app.services.cutting_result_validator import validate_cutting_result
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting


DEFAULT_PARTS_TEXT = """A1; Боковина; 720; 500; 2
A2; Полка; 680; 300; 3
A3; Цоколь; 680; 100; 2"""


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


@dataclass(frozen=True)
class ManualCuttingPreview:
	result: CuttingResult | None
	issues: list[ResultIssue]
	svg: str | None
	input_errors: list[str]


@dataclass(frozen=True)
class _ParsedManualForm:
	sheet_width_mm: float
	sheet_height_mm: float
	sheet_quantity: int
	kerf_width_mm: float
	initial_cut_direction: CutDirection
	margins: SheetMargins
	errors: list[str]


def make_default_manual_cutting_form() -> ManualCuttingFormData:
	return ManualCuttingFormData(
		sheet_width_mm="2800",
		sheet_height_mm="2070",
		sheet_quantity="1",
		kerf_width_mm="4",
		margin_left_mm="10",
		margin_top_mm="10",
		margin_right_mm="10",
		margin_bottom_mm="10",
		parts_text=DEFAULT_PARTS_TEXT,
		initial_cut_direction=CutDirection.VERTICAL.value,
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
	)


def build_manual_cutting_preview(form: ManualCuttingFormData) -> ManualCuttingPreview:
	parsed_form = _parse_manual_form(form)
	parts_result = parse_manual_parts_text(form.parts_text)

	input_errors = [*parsed_form.errors]
	input_errors.extend(
		f"Строка {error.line_number}: {error.message} Текст: {error.line_text}"
		for error in parts_result.errors
	)

	if not parts_result.parts:
		input_errors.append("Добавь хотя бы одну корректную деталь.")

	if input_errors:
		return ManualCuttingPreview(
			result=None,
			issues=[],
			svg=None,
			input_errors=input_errors,
		)

	sheet = SheetInput(
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
		parts=parts_result.parts,
		sheets=[sheet],
		settings=settings,
	)
	issues = validate_cutting_result(result)
	svg = svg_exporter.export_cutting_result_to_svg(result, issues=issues)

	return ManualCuttingPreview(
		result=result,
		issues=issues,
		svg=svg,
		input_errors=[],
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
		errors=errors,
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


def _first(values: dict[str, list[str]], name: str, default: str) -> str:
	items = values.get(name)
	if not items:
		return default
	return items[0]


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
