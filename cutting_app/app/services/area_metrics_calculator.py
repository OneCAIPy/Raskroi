def calculate_material_utilization_percent(
	*,
	placed_area_mm2: float,
	used_material_area_mm2: float,
) -> float:
	return _calculate_area_ratio_percent(
		placed_area_mm2=placed_area_mm2,
		reference_area_mm2=used_material_area_mm2,
	)


def calculate_material_utilization_with_return_remnants_percent(
	*,
	placed_area_mm2: float,
	return_remnant_area_mm2: float,
	used_material_area_mm2: float,
) -> float:
	return _calculate_area_ratio_percent(
		placed_area_mm2=placed_area_mm2 + return_remnant_area_mm2,
		reference_area_mm2=used_material_area_mm2,
	)


def calculate_working_area_efficiency_percent(
	*,
	placed_area_mm2: float,
	working_area_mm2: float,
) -> float:
	return _calculate_area_ratio_percent(
		placed_area_mm2=placed_area_mm2,
		reference_area_mm2=working_area_mm2,
	)


def _calculate_area_ratio_percent(
	*,
	placed_area_mm2: float,
	reference_area_mm2: float,
) -> float:
	if reference_area_mm2 <= 0:
		return 0

	return placed_area_mm2 / reference_area_mm2 * 100
