from dataclasses import dataclass
from math import isfinite

from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.services.validation_service import validate_sheet_input


@dataclass(frozen=True)
class EditableRemnantRow:
	width_mm: str = ""
	height_mm: str = ""
	quantity: str = ""


@dataclass(frozen=True)
class EditableRemnantRowError:
	row_number: int
	message: str


@dataclass(frozen=True)
class EditableRemnantsImportResult:
	sheets: list[SheetInput]
	errors: list[EditableRemnantRowError]


def parse_editable_remnant_rows(
	rows: list[EditableRemnantRow] | tuple[EditableRemnantRow, ...],
	*,
	margins: SheetMargins,
) -> EditableRemnantsImportResult:
	sheets: list[SheetInput] = []
	errors: list[EditableRemnantRowError] = []

	for row_number, row in enumerate(rows, start=1):
		if _is_empty_row(row):
			continue

		sheet, row_errors = _parse_editable_remnant_row(
			row,
			row_number=row_number,
			margins=margins,
		)
		if row_errors:
			errors.append(
				EditableRemnantRowError(
					row_number=row_number,
					message=" ".join(row_errors),
				)
			)
			continue

		if sheet is None:
			raise ValueError("Строка без ошибок должна содержать дополнительный кусок.")
		sheets.append(sheet)

	return EditableRemnantsImportResult(sheets=sheets, errors=errors)


def _is_empty_row(row: EditableRemnantRow) -> bool:
	return (
		not row.width_mm.strip()
		and not row.height_mm.strip()
		and row.quantity.strip() in ("", "1")
	)


def _parse_editable_remnant_row(
	row: EditableRemnantRow,
	*,
	row_number: int,
	margins: SheetMargins,
) -> tuple[SheetInput | None, list[str]]:
	width_mm = _parse_positive_float(row.width_mm, "Ширина")
	height_mm = _parse_positive_float(row.height_mm, "Высота")
	quantity = _parse_positive_int(row.quantity or "1", "Количество")
	errors = [
		value
		for value in (width_mm, height_mm, quantity)
		if isinstance(value, str)
	]
	if errors:
		return None, errors

	sheet = SheetInput(
		name=f"Дополнительный кусок {row_number}",
		width_mm=width_mm,
		height_mm=height_mm,
		quantity=quantity,
		is_remnant=True,
		margins=margins,
	)
	sheet_issues = validate_sheet_input(sheet)
	if sheet_issues:
		return None, [issue.message for issue in sheet_issues]

	return sheet, []


def _parse_positive_float(value: str, field_name: str) -> float | str:
	try:
		parsed = float(value.replace(",", "."))
	except ValueError:
		return f"{field_name}: должно быть число."

	if not isfinite(parsed) or parsed <= 0:
		return f"{field_name}: должно быть больше 0."

	return parsed


def _parse_positive_int(value: str, field_name: str) -> int | str:
	try:
		parsed = int(value)
	except ValueError:
		return f"{field_name}: должно быть целое число."

	if parsed <= 0:
		return f"{field_name}: должно быть больше 0."

	return parsed
