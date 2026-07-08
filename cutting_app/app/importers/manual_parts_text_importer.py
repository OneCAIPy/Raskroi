from dataclasses import dataclass

from cutting_app.app.domain.edge import EdgeSet
from cutting_app.app.domain.part import PartInput


@dataclass(frozen=True)
class ManualPartLineError:
	line_number: int
	message: str
	line_text: str


@dataclass(frozen=True)
class ManualPartsImportResult:
	parts: list[PartInput]
	errors: list[ManualPartLineError]


_FIELD_COUNT = 5


def parse_manual_parts_text(text: str) -> ManualPartsImportResult:
	parts: list[PartInput] = []
	errors: list[ManualPartLineError] = []

	for line_number, raw_line in enumerate(text.splitlines(), start=1):
		line = raw_line.strip()
		if not line:
			continue

		fields = [field.strip() for field in line.split(";")]
		if len(fields) != _FIELD_COUNT:
			errors.append(
				ManualPartLineError(
					line_number=line_number,
					message="Ожидается 5 полей: номер; название; L; W; количество.",
					line_text=raw_line,
				)
			)
			continue

		number, name, l_text, w_text, quantity_text = fields
		line_errors = _validate_required_text(number, name)
		l_mm = _parse_positive_float(l_text, "L")
		w_mm = _parse_positive_float(w_text, "W")
		quantity = _parse_positive_int(quantity_text, "количество")

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

		parts.append(
			PartInput(
				number=number,
				name=name,
				l_mm=l_mm,
				w_mm=w_mm,
				quantity=quantity,
				edges=EdgeSet(),
			)
		)

	return ManualPartsImportResult(parts=parts, errors=errors)


def _validate_required_text(number: str, name: str) -> list[str]:
	errors: list[str] = []
	if not number:
		errors.append("Номер детали не заполнен.")
	if not name:
		errors.append("Название детали не заполнено.")
	return errors


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
