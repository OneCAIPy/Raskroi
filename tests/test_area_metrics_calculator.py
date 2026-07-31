import pytest

from cutting_app.app.services.area_metrics_calculator import (
	calculate_material_utilization_percent,
	calculate_working_area_efficiency_percent,
)


def test_material_utilization_matches_basis_reference_order() -> None:
	placed_area_mm2 = 39_201_903
	used_material_area_mm2 = 13 * 2800 * 1220

	result = calculate_material_utilization_percent(
		placed_area_mm2=placed_area_mm2,
		used_material_area_mm2=used_material_area_mm2,
	)

	assert result == pytest.approx(88.27666861826698)
	assert round(result, 2) == 88.28


def test_working_area_efficiency_uses_area_after_sheet_trims() -> None:
	placed_area_mm2 = 39_201_903
	working_area_mm2 = 13 * 2770 * 1200

	result = calculate_working_area_efficiency_percent(
		placed_area_mm2=placed_area_mm2,
		working_area_mm2=working_area_mm2,
	)

	assert result == pytest.approx(90.71994584837545)
	assert round(result, 2) == 90.72


@pytest.mark.parametrize(
	"calculator, denominator_name",
	[
		(calculate_material_utilization_percent, "used_material_area_mm2"),
		(calculate_working_area_efficiency_percent, "working_area_mm2"),
	],
)
def test_area_metric_is_zero_when_denominator_is_zero(calculator, denominator_name) -> None:
	result = calculator(placed_area_mm2=0, **{denominator_name: 0})

	assert result == 0
