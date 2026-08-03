from dataclasses import dataclass

from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.validation_service import validate_part_input


@dataclass(frozen=True)
class ManualPartLineError:
	line_number: int
	message: str
	line_text: str


@dataclass(frozen=True)
class ManualPartsImportResult:
	parts: list[PartInput]
	errors: list[ManualPartLineError]


_BASIC_FIELD_COUNT = 5
_EXTENDED_FIELD_COUNT = 9
_EDGE_SIDE_NAMES = ("L1", "L2", "W1", "W2")


def parse_manual_parts_text(text: str) -> ManualPartsImportResult:
	parts: list[PartInput] = []
	errors: list[ManualPartLineError] = []

	for line_number, raw_line in enumerate(text.splitlines(), start=1):
		line = raw_line.strip()
		if not line:
			continue

		fields = [field.strip() for field in line.split(";")]
		if len(fields) not in (_BASIC_FIELD_COUNT, _EXTENDED_FIELD_COUNT):
			errors.append(
				ManualPartLineError(
					line_number=line_number,
					message=(
						"Ожидается 5 или 9 полей: номер; название; L; W; "
						"количество; при расширенном формате — L1; L2; W1; W2."
					),
					line_text=raw_line,
				)
			)
			continue

		number, name, l_text, w_text, quantity_text = fields[:_BASIC_FIELD_COUNT]
		line_errors = _validate_required_text(number, name)
		l_mm = _parse_positive_float(l_text, "L")
		w_mm = _parse_positive_float(w_text, "W")
		quantity = _parse_positive_int(quantity_text, "количество")
		edges, edge_errors = _parse_edges(fields[_BASIC_FIELD_COUNT:])
		line_errors.extend(edge_errors)

		for parsed_value in [l_mm, w_mm, quantity]:
			if isinstance(parsed_value, str):
				line_errors.append(parsed_value)

		if line_errors:
			errors.append(
				ManualPartLineError(
					line_number=line_number,
					message=" ".join(line_errors),
					line_text=raw_line,
				)
			)
			continue

		part = PartInput(
			number=number,
			name=name,
			l_mm=l_mm,
			w_mm=w_mm,
			quantity=quantity,
			edges=edges,
		)
		part_issues = validate_part_input(part)
		if part_issues:
			errors.append(
				ManualPartLineError(
					line_number=line_number,
					message=" ".join(issue.message for issue in part_issues),
					line_text=raw_line,
				)
			)
			continue

		parts.append(part)

	return ManualPartsImportResult(parts=parts, errors=errors)


def _validate_required_text(number: str, name: str) -> list[str]:
	errors: list[str] = []
	if not number:
		errors.append("Номер детали не заполнен.")
	if not name:
		errors.append("Название детали не заполнено.")
	return errors


def _parse_edges(fields: list[str]) -> tuple[EdgeSet, list[str]]:
	if not fields:
		return EdgeSet(), []

	specs: list[EdgeSpec] = []
	errors: list[str] = []

	for side_name, value in zip(_EDGE_SIDE_NAMES, fields, strict=True):
		spec, spec_errors = _parse_edge_spec(value, side_name)
		specs.append(spec)
		errors.extend(spec_errors)

	return (
		EdgeSet(
			L1=specs[0],
			L2=specs[1],
			W1=specs[2],
			W2=specs[3],
		),
		errors,
	)


def _parse_edge_spec(value: str, side_name: str) -> tuple[EdgeSpec, list[str]]:
	if value.strip() in ("", "-", "—"):
		return EdgeSpec(), []

	parameters = [parameter.strip() for parameter in value.split("|")]
	if len(parameters) > 4:
		return EdgeSpec(), [
			f"Кромка {side_name}: ожидается не более 4 параметров — "
			"толщина|прифуговка|свес|материал."
		]

	parameters.extend([""] * (4 - len(parameters)))
	thickness_text, trimming_text, overhang_text, material_name = parameters
	thickness_mm = _parse_positive_float(
		thickness_text,
		f"толщина кромки {side_name}",
	)
	trimming_allowance_mm = _parse_non_negative_float(
		trimming_text,
		"прифуговка",
	)
	tape_overhang_mm = _parse_non_negative_float(
		overhang_text,
		"свес",
	)

	errors = [
		parsed_value
		for parsed_value in [
			thickness_mm,
			trimming_allowance_mm,
			tape_overhang_mm,
		]
		if isinstance(parsed_value, str)
	]
	if errors:
		return EdgeSpec(), [
			f"Кромка {side_name}: {message}"
			for message in errors
		]

	return (
		EdgeSpec(
			thickness_mm=thickness_mm,
			trimming_allowance_mm=trimming_allowance_mm,
			tape_overhang_mm=tape_overhang_mm,
			material_name=material_name,
		),
		[],
	)


def _parse_positive_float(value: str, field_name: str) -> float | str:
	try:
		parsed = float(value.replace(",", "."))
	except ValueError:
		return f"Поле {field_name} должно быть числом."

	if parsed <= 0:
		return f"Поле {field_name} должно быть больше 0."

	return parsed


def _parse_positive_int(value: str, field_name: str) -> int | str:
	try:
		parsed = int(value)
	except ValueError:
		return f"Поле {field_name} должно быть целым числом."

	if parsed <= 0:
		return f"Поле {field_name} должно быть больше 0."

	return parsed


def _parse_non_negative_float(value: str, field_name: str) -> float | str:
	if not value:
		return 0.0

	try:
		parsed = float(value.replace(",", "."))
	except ValueError:
		return f"Параметр «{field_name}» должен быть числом."

	if parsed < 0:
		return f"Параметр «{field_name}» должен быть не меньше 0."

	return parsed
