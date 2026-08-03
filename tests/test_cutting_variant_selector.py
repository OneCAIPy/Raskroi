from dataclasses import replace

import pytest

from cutting_app.app.domain.cut_tree import CutNode, RectArea
from cutting_app.app.domain.cutting_result import (
	CuttingMetrics,
	CuttingResult,
	SheetCutResult,
)
from cutting_app.app.domain.optimization import OptimizationVariantScore
from cutting_app.app.domain.production_cut_plan import (
	ProductionCutPlan,
	ProductionCutPlanMetrics,
)
from cutting_app.app.domain.return_remnant import (
	ReturnRemnantProfile,
	ReturnRemnantSettings,
)
from cutting_app.app.services.cutting_variant_selector import (
	EvaluatedCuttingVariant,
	select_best_cutting_variant,
)


def test_variant_score_prioritizes_complete_placement_over_all_later_metrics() -> None:
	complete = _score(
		unplaced_part_count=0,
		placed_area_mm2=100,
		new_sheet_count=2,
		new_material_area_mm2=2_000_000,
		return_remnant_area_mm2=0,
		cut_length_mm=1000,
		pass_count=20,
		strip_turn_count=10,
		size_setting_count=10,
		technical_order=10,
	)
	incomplete = _score(
		unplaced_part_count=1,
		placed_area_mm2=1000,
		new_sheet_count=0,
		new_material_area_mm2=0,
		return_remnant_area_mm2=10_000_000,
		cut_length_mm=0,
		pass_count=0,
		strip_turn_count=0,
		size_setting_count=0,
		technical_order=0,
	)

	assert complete.selection_key < incomplete.selection_key


def test_variant_score_uses_explicit_material_profile_and_production_order() -> None:
	base = _score(
		unplaced_part_count=0,
		placed_area_mm2=1000,
		new_sheet_count=2,
		new_material_area_mm2=2_000_000,
		return_remnant_area_mm2=300_000,
		cut_length_mm=100,
		pass_count=10,
		strip_turn_count=5,
		size_setting_count=4,
		technical_order=3,
	)

	assert base.selection_key < replace(base, placed_area_mm2=999).selection_key
	assert base.selection_key < replace(base, new_sheet_count=3).selection_key
	assert base.selection_key < replace(base, new_material_area_mm2=2_000_001).selection_key
	assert base.selection_key < replace(base, return_remnant_area_mm2=299_999).selection_key
	assert base.selection_key < replace(base, cut_length_mm=101).selection_key
	assert base.selection_key < replace(base, pass_count=11).selection_key
	assert base.selection_key < replace(base, strip_turn_count=6).selection_key
	assert base.selection_key < replace(base, size_setting_count=5).selection_key
	assert base.selection_key < replace(base, technical_order=4).selection_key

	fewer_new_sheets = replace(
		base,
		new_sheet_count=1,
		new_material_area_mm2=10_000_000,
		return_remnant_area_mm2=0,
		cut_length_mm=10000,
	)
	more_new_sheets = replace(
		base,
		new_sheet_count=2,
		new_material_area_mm2=1,
		return_remnant_area_mm2=10_000_000,
		cut_length_mm=0,
	)
	assert fewer_new_sheets.selection_key < more_new_sheets.selection_key

	better_remnant = replace(base, return_remnant_area_mm2=300_001, cut_length_mm=10000)
	worse_remnant = replace(base, return_remnant_area_mm2=300_000, cut_length_mm=0)
	assert better_remnant.selection_key < worse_remnant.selection_key


@pytest.mark.parametrize(
	("profile", "expected_variant_id"),
	[
		(ReturnRemnantProfile.MAX_USEFUL_AREA, "max-area"),
		(ReturnRemnantProfile.LONG, "long"),
		(ReturnRemnantProfile.COMPACT, "compact"),
	],
)
def test_selector_applies_selected_return_remnant_profile(
	profile: ReturnRemnantProfile,
	expected_variant_id: str,
) -> None:
	candidates = [
		_candidate("max-area", 1, _result(remnant_size=(1000, 500))),
		_candidate("long", 2, _result(remnant_size=(1400, 200))),
		_candidate("compact", 3, _result(remnant_size=(700, 600))),
	]

	selected = select_best_cutting_variant(
		candidates,
		return_remnant_settings=ReturnRemnantSettings(value_profile=profile),
	)

	assert selected.optimization is not None
	assert selected.optimization.selected_variant_id == expected_variant_id
	assert selected.optimization.score.return_remnant_profile == profile


def test_selector_minimizes_new_material_before_return_remnant_profile() -> None:
	input_remnant_result = _result(
		remnant_size=(100, 100),
		sheet_is_remnant=True,
		sheet_width_mm=2000,
		sheet_height_mm=1000,
	)
	new_sheet_result = _result(
		remnant_size=(1800, 900),
		sheet_is_remnant=False,
		sheet_width_mm=2000,
		sheet_height_mm=1000,
	)

	selected = select_best_cutting_variant(
		[
			_candidate("new-sheet", 1, new_sheet_result),
			_candidate("input-remnant", 2, input_remnant_result),
		],
		return_remnant_settings=ReturnRemnantSettings(
			value_profile=ReturnRemnantProfile.MAX_USEFUL_AREA,
		),
	)

	assert selected.optimization is not None
	assert selected.optimization.selected_variant_id == "input-remnant"
	assert selected.optimization.score.new_sheet_count == 0
	assert selected.optimization.score.new_material_area_mm2 == 0


def test_selector_minimizes_new_material_area_after_new_sheet_count() -> None:
	smaller_sheet_result = _result(
		remnant_size=(100, 100),
		sheet_width_mm=1000,
		sheet_height_mm=1000,
	)
	larger_sheet_result = _result(
		remnant_size=(1800, 900),
		sheet_width_mm=2000,
		sheet_height_mm=1000,
	)

	selected = select_best_cutting_variant(
		[
			_candidate("larger-sheet", 1, larger_sheet_result),
			_candidate("smaller-sheet", 2, smaller_sheet_result),
		],
	)

	assert selected.optimization is not None
	assert selected.optimization.selected_variant_id == "smaller-sheet"
	assert selected.optimization.score.new_sheet_count == 1
	assert selected.optimization.score.new_material_area_mm2 == 1_000_000


def test_selector_uses_technical_order_for_stable_complete_tie() -> None:
	result = _result()
	candidates = [
		EvaluatedCuttingVariant(
			variant_id="later",
			technical_order=2,
			result=result,
		),
		EvaluatedCuttingVariant(
			variant_id="first",
			technical_order=1,
			result=result,
		),
	]

	selected = select_best_cutting_variant(candidates)

	assert selected.optimization is not None
	assert selected.optimization.selected_variant_id == "first"
	assert selected.optimization.evaluated_variant_count == 2
	assert selected.optimization.score.technical_order == 1


def test_selector_rejects_empty_variant_list() -> None:
	with pytest.raises(ValueError, match="вариант"):
		select_best_cutting_variant([])


def _score(**values) -> OptimizationVariantScore:
	defaults = {
		"sheet_count": 2,
		"material_utilization_percent": 50,
		"new_sheet_count": 2,
		"new_material_area_mm2": 2_000_000,
		"return_remnant_profile": ReturnRemnantProfile.MAX_USEFUL_AREA,
		"return_remnant_area_mm2": 0,
		"largest_return_remnant_area_mm2": 0,
		"longest_return_remnant_side_mm": 0,
		"longest_return_remnant_area_mm2": 0,
		"largest_compact_square_area_mm2": 0,
		"compact_return_remnant_area_mm2": 0,
	}
	defaults.update(values)
	return OptimizationVariantScore(**defaults)


def _candidate(
	variant_id: str,
	technical_order: int,
	result: CuttingResult,
) -> EvaluatedCuttingVariant:
	return EvaluatedCuttingVariant(
		variant_id=variant_id,
		technical_order=technical_order,
		result=result,
	)


def _result(
	*,
	remnant_size: tuple[float, float] = (100, 100),
	sheet_is_remnant: bool = False,
	sheet_width_mm: float = 2000,
	sheet_height_mm: float = 1000,
) -> CuttingResult:
	area = RectArea(
		x_mm=0,
		y_mm=0,
		width_mm=remnant_size[0],
		height_mm=remnant_size[1],
	)
	plan = ProductionCutPlan(
		plan_id="Лист",
		source_area=area,
		metrics=ProductionCutPlanMetrics(
			cycle_count=1,
			strip_turn_count=2,
			size_setting_count=3,
			pass_count=4,
			cut_length_mm=500,
		),
	)
	sheet = SheetCutResult(
		sheet_name="Лист",
		sheet_width_mm=sheet_width_mm,
		sheet_height_mm=sheet_height_mm,
		root=CutNode(area=area, is_waste=True),
		sheet_is_remnant=sheet_is_remnant,
		production_cut_plan=plan,
	)

	return CuttingResult(
		sheets=[sheet],
		metrics=CuttingMetrics(
			sheet_count=1,
			placed_part_count=1,
			unplaced_part_count=0,
			placed_area_mm2=5000,
			material_utilization_percent=50,
		),
	)
