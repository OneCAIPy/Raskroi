from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.return_remnant import ReturnRemnantProfile


_PROFILE_LABELS = {
	ReturnRemnantProfile.MAX_USEFUL_AREA: "максимальная полезная площадь",
	ReturnRemnantProfile.LONG: "длинный остаток",
	ReturnRemnantProfile.COMPACT: "компактный остаток",
}


def export_cutting_result_to_txt(result: CuttingResult) -> str:
	metrics = result.metrics
	production_metrics = _production_metrics(result)
	lines = [
		_row("Количество плит материала", metrics.standard_sheet_count),
		_row(
			"Количество использованных дополнительных кусков",
			metrics.input_remnant_count,
		),
		"",
		_row("КИМ", f"{_format_decimal(metrics.material_utilization_percent, 2)} %"),
		_row(
			"КИМ с учетом обрезков",
			f"{_format_decimal(metrics.material_utilization_with_return_remnants_percent, 2)} %",
		),
		_row(
			"Площадь использованных плит и дополнительных кусков",
			f"{_format_decimal(metrics.sheet_area_mm2 / 1_000_000, 3)} кв.м.",
		),
		_row(
			"Площадь панелей",
			f"{_format_decimal(metrics.placed_area_mm2 / 1_000_000, 3)} кв.м.",
		),
		_row(
			"Площадь возвратных обрезков",
			f"{_format_decimal(metrics.return_remnant_area_mm2 / 1_000_000, 3)} кв.м.",
		),
		_row(
			"Заполнение рабочей области",
			f"{_format_decimal(metrics.working_area_efficiency_percent, 2)} %",
		),
		"",
		_row(
			"Длина резов (проходов)",
			f"{_format_decimal(production_metrics['cut_length_mm'] / 1000, 4)} м.",
		),
		"",
		_row("Облицовка", _edge_material_names(result)),
		_row(
			"Длина облицовки",
			f"{_format_decimal(result.edge_consumption.base_length_mm / 1000, 3)} м.",
		),
		_row(
			"Длина облицовки с учетом свесов",
			f"{_format_decimal(result.edge_consumption.total_length_mm / 1000, 3)} м.",
		),
		_row(
			"Количество отрезов облицовки",
			result.edge_consumption.segment_count,
		),
		"",
		_row("Количество карт раскроя", metrics.sheet_count),
		_row("Количество панелей", metrics.placed_part_count),
		_row("Количество неразмещённых панелей", metrics.unplaced_part_count),
		_row("Количество возвратных обрезков", metrics.return_remnant_count),
		_row("Количество поворотов полос", production_metrics["strip_turn_count"]),
		_row("Количество установок размеров", production_metrics["size_setting_count"]),
		_row("Количество резов (проходов)", production_metrics["pass_count"]),
		"",
		_row("Профиль возвратного остатка", _return_remnant_profile_label(result)),
		"",
		"Обрезки",
	]
	lines.extend(
		f"\t{_format_number(remnant.long_side_mm)}\t"
		f"{_format_number(remnant.short_side_mm)}\t1"
		for remnant in result.return_remnants
	)

	return "\ufeff" + "\r\n".join(lines) + "\r\n"


def _production_metrics(result: CuttingResult) -> dict[str, float | int]:
	if result.optimization is None:
		return {
			"cut_length_mm": 0.0,
			"pass_count": 0,
			"strip_turn_count": 0,
			"size_setting_count": 0,
		}

	score = result.optimization.score
	return {
		"cut_length_mm": score.cut_length_mm,
		"pass_count": score.pass_count,
		"strip_turn_count": score.strip_turn_count,
		"size_setting_count": score.size_setting_count,
	}


def _edge_material_names(result: CuttingResult) -> str:
	if not result.edge_consumption.by_material:
		return "Не задана"

	names: list[str] = []
	for item in result.edge_consumption.by_material:
		name = item.material_name or "Не указан"
		if name not in names:
			names.append(name)
	return "; ".join(names)


def _return_remnant_profile_label(result: CuttingResult) -> str:
	if result.optimization is None:
		return "не задан"
	return _PROFILE_LABELS[result.optimization.score.return_remnant_profile]


def _row(label: str, value: object) -> str:
	return f"{label}\t{value}"


def _format_decimal(value: float, decimal_places: int) -> str:
	return f"{value:.{decimal_places}f}".replace(".", ",")


def _format_number(value: float) -> str:
	return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", ",")
