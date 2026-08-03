import pytest

from cutting_app.app.domain.cut_tree import CutDirection, CutLine, CutNode, RectArea
from cutting_app.app.domain.return_remnant import (
	ReturnRemnantProfile,
	ReturnRemnantSettings,
)
from cutting_app.app.services.return_remnant_calculator import (
	collect_return_remnants,
	meets_return_remnant_thresholds,
)
from tests.basis_agt_3019_fixture import BASIS_AGT_3019_RETURN_REMNANTS


def test_only_qualifying_waste_leaves_are_return_remnants() -> None:
	part_leaf = CutNode(
		area=RectArea(x_mm=0, y_mm=0, width_mm=400, height_mm=600),
		part_number="1",
	)
	waste_leaf = CutNode(
		area=RectArea(x_mm=404, y_mm=0, width_mm=596, height_mm=600),
		is_waste=True,
	)
	root = CutNode(
		area=RectArea(x_mm=0, y_mm=0, width_mm=1000, height_mm=600),
		cut=CutLine(
			direction=CutDirection.VERTICAL,
			position_mm=400,
			kerf_width_mm=4,
		),
		first=part_leaf,
		second=waste_leaf,
		is_waste=True,
	)

	remnants = collect_return_remnants(
		root=root,
		sheet_name="Лист #1",
		settings=ReturnRemnantSettings(),
	)

	assert len(remnants) == 1
	assert remnants[0].sheet_name == "Лист #1"
	assert remnants[0].area == waste_leaf.area
	assert remnants[0].area_mm2 == 357_600
	assert remnants[0].long_side_mm == 600
	assert remnants[0].short_side_mm == 596


@pytest.mark.parametrize(
	"area",
	[
		RectArea(x_mm=0, y_mm=0, width_mm=399.9, height_mm=200),
		RectArea(x_mm=0, y_mm=0, width_mm=500, height_mm=79.9),
		RectArea(x_mm=0, y_mm=0, width_mm=400, height_mm=80),
	],
)
def test_each_return_remnant_threshold_is_required(area: RectArea) -> None:
	assert not meets_return_remnant_thresholds(
		area,
		ReturnRemnantSettings(
			min_long_side_mm=400,
			min_short_side_mm=80,
			min_area_mm2=40_000,
		),
	)


def test_return_remnant_threshold_boundaries_are_inclusive() -> None:
	assert meets_return_remnant_thresholds(
		RectArea(x_mm=0, y_mm=0, width_mm=500, height_mm=80),
		ReturnRemnantSettings(
			min_long_side_mm=500,
			min_short_side_mm=80,
			min_area_mm2=40_000,
		),
	)


def test_return_remnant_settings_validate_and_normalize_profile() -> None:
	settings = ReturnRemnantSettings(value_profile="long")

	assert settings.value_profile == ReturnRemnantProfile.LONG

	with pytest.raises(ValueError, match="профиль"):
		ReturnRemnantSettings(value_profile="triangle")


def test_basis_reference_has_17_return_remnants_with_expected_area() -> None:
	settings = ReturnRemnantSettings()
	areas = [
		RectArea(x_mm=0, y_mm=0, width_mm=width_mm, height_mm=height_mm)
		for width_mm, height_mm in BASIS_AGT_3019_RETURN_REMNANTS
	]

	assert len(areas) == 17
	assert all(meets_return_remnant_thresholds(area, settings) for area in areas)
	assert sum(area.width_mm * area.height_mm for area in areas) == pytest.approx(
		2_555_169.2
	)
	assert not meets_return_remnant_thresholds(
		RectArea(x_mm=0, y_mm=0, width_mm=359, height_mm=148.6),
		settings,
	)
