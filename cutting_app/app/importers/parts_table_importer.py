from dataclasses import dataclass
from math import isfinite

from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.validation_service import validate_part_input


@dataclass(frozen=True)
class EditablePartRow:
	number: str = ""
	name: str = ""
	l_mm: str = ""
	w_mm: str = ""
	quantity: str = ""
	rotation_allowed: bool = True
	L1: bool = False
	L2: bool = False
	W1: bool = False
	W2: bool = False

	@property
	def has_edge(self) -> bool:
		return self.L1 or self.L2 or self.W1 or self.W2


@dataclass(frozen=True)
class EditablePartRowError:
	row_number: int
	message: str


@dataclass(frozen=True)
class EditablePartsImportResult:
	parts: list[PartInput]
	errors: list[EditablePartRowError]


def parse_editable_part_rows(
	rows: list[EditablePartRow] | tuple[EditablePartRow, ...],
	*,
	edge_thickness_mm: str,
	edge_trimming_allowance_mm: str,
	edge_material_name: str,
) -> EditablePartsImportResult:
	parts: list[PartInput] = []
	errors: list[EditablePartRowError] = []

	for row_number, row in enumerate(rows, start=1):
		part, row_errors = _parse_editable_part_row(
			row,
			edge_thickness_mm=edge_thickness_mm,
			edge_trimming_allowance_mm=edge_trimming_allowance_mm,
			edge_material_name=edge_material_name,
		)
		if row_errors:
			errors.append(
				EditablePartRowError(
					row_number=row_number,
					message=" ".join(row_errors),
				)
			)
			continue

		if part is None:
			raise ValueError("Строка без ошибок должна содержать деталь.")
		parts.append(part)

	return EditablePartsImportResult(parts=parts, errors=errors)


def _parse_editable_part_row(
	row: EditablePartRow,
	*,
	edge_thickness_mm: str,
	edge_trimming_allowance_mm: str,
	edge_material_name: str,
) -> tuple[PartInput | None, list[str]]:
	errors: list[str] = []
	number = row.number.strip()
	name = row.name.strip()
	if not number:
		errors.append("Номер детали не заполнен.")
	if not name:
		errors.append("Название детали не заполнено.")

	l_mm = _parse_positive_float(row.l_mm, "L")
	w_mm = _parse_positive_float(row.w_mm, "W")
	quantity = _parse_positive_int(row.quantity, "количество")
	for parsed_value in (l_mm, w_mm, quantity):
		if isinstance(parsed_value, str):
			errors.append(parsed_value)

	edge_spec = EdgeSpec()
	if row.has_edge:
		edge_spec, edge_errors = _parse_common_edge_spec(
			edge_thickness_mm=edge_thickness_mm,
			edge_trimming_allowance_mm=edge_trimming_allowance_mm,
			edge_material_name=edge_material_name,
		)
		errors.extend(edge_errors)

	if errors:
		return None, errors

	part = PartInput(
		number=number,
		name=name,
		l_mm=l_mm,
		w_mm=w_mm,
		quantity=quantity,
		rotation_allowed=row.rotation_allowed,
		edges=EdgeSet(
			L1=edge_spec if row.L1 else EdgeSpec(),
			L2=edge_spec if row.L2 else EdgeSpec(),
			W1=edge_spec if row.W1 else EdgeSpec(),
			W2=edge_spec if row.W2 else EdgeSpec(),
		),
	)
	part_issues = validate_part_input(part)
	if part_issues:
		return None, [issue.message for issue in part_issues]

	return part, []


def _parse_common_edge_spec(
	*,
	edge_thickness_mm: str,
	edge_trimming_allowance_mm: str,
	edge_material_name: str,
) -> tuple[EdgeSpec, list[str]]:
	thickness_mm = _parse_positive_float(
		edge_thickness_mm,
		"Толщина кромки",
	)
	trimming_allowance_mm = _parse_non_negative_float(
		edge_trimming_allowance_mm,
		"Прифуговка",
	)
	errors = [
		value
		for value in (thickness_mm, trimming_allowance_mm)
		if isinstance(value, str)
	]
	if errors:
		return EdgeSpec(), errors

	return (
		EdgeSpec(
			thickness_mm=thickness_mm,
			trimming_allowance_mm=trimming_allowance_mm,
			material_name=edge_material_name.strip(),
		),
		[],
	)


def _parse_positive_float(value: str, field_name: str) -> float | str:
	try:
		parsed = float(value.replace(",", "."))
	except ValueError:
		return f"Поле {field_name} должно быть числом."

	if not isfinite(parsed) or parsed <= 0:
		return f"Поле {field_name} должно быть больше 0."

	return parsed


def _parse_non_negative_float(value: str, field_name: str) -> float | str:
	if not value.strip():
		return 0.0

	try:
		parsed = float(value.replace(",", "."))
	except ValueError:
		return f"{field_name}: должно быть числом."

	if not isfinite(parsed) or parsed < 0:
		return f"{field_name}: должно быть не меньше 0."

	return parsed


def _parse_positive_int(value: str, field_name: str) -> int | str:
	try:
		parsed = int(value)
	except ValueError:
		return f"Поле {field_name} должно быть целым числом."

	if parsed <= 0:
		return f"Поле {field_name} должно быть больше 0."

	return parsed
