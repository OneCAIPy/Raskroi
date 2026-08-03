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
from cutting_app.app.services.cutting_variant_selector import (
	EvaluatedCuttingVariant,
	select_best_cutting_variant,
)


def test_variant_score_prioritizes_complete_placement_over_all_later_metrics() -> None:
	complete = _score(
		unplaced_part_count=0,
		placed_area_mm2=100,
		sheet_count=2,
		material_utilization_percent=50,
		cut_length_mm=1000,
		pass_count=20,
		strip_turn_count=10,
		size_setting_count=10,
		technical_order=10,
	)
	incomplete = _score(
		unplaced_part_count=1,
		placed_area_mm2=1000,
		sheet_count=1,
		material_utilization_percent=100,
		cut_length_mm=0,
		pass_count=0,
		strip_turn_count=0,
		size_setting_count=0,
		technical_order=0,
	)

	assert complete.selection_key < incomplete.selection_key


def test_variant_score_uses_explicit_lexicographic_production_order() -> None:
	base = _score(
		unplaced_part_count=0,
		placed_area_mm2=1000,
		sheet_count=2,
		material_utilization_percent=80,
		cut_length_mm=100,
		pass_count=10,
		strip_turn_count=5,
		size_setting_count=4,
		technical_order=3,
	)

	assert base.selection_key < replace(base, placed_area_mm2=999).selection_key
	assert base.selection_key < replace(base, sheet_count=3).selection_key
	assert base.selection_key < replace(base, material_utilization_percent=79).selection_key
	assert base.selection_key < replace(base, cut_length_mm=101).selection_key
	assert base.selection_key < replace(base, pass_count=11).selection_key
	assert base.selection_key < replace(base, strip_turn_count=6).selection_key
	assert base.selection_key < replace(base, size_setting_count=5).selection_key
	assert base.selection_key < replace(base, technical_order=4).selection_key

	fewer_sheets = replace(
		base,
		sheet_count=1,
		material_utilization_percent=1,
		cut_length_mm=10000,
	)
	more_sheets = replace(
		base,
		sheet_count=2,
		material_utilization_percent=100,
		cut_length_mm=0,
	)
	assert fewer_sheets.selection_key < more_sheets.selection_key

	higher_utilization = replace(base, material_utilization_percent=81, cut_length_mm=10000)
	lower_utilization = replace(base, material_utilization_percent=80, cut_length_mm=0)
	assert higher_utilization.selection_key < lower_utilization.selection_key


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
	return OptimizationVariantScore(**values)


def _result() -> CuttingResult:
	area = RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100)
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
		sheet_width_mm=100,
		sheet_height_mm=100,
		root=CutNode(area=area, is_waste=True),
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
