from dataclasses import dataclass, replace

from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.optimization import (
	OptimizationSummary,
	OptimizationVariantScore,
)
from cutting_app.app.domain.return_remnant import ReturnRemnantSettings
from cutting_app.app.services.return_remnant_calculator import (
	collect_cutting_result_return_remnants,
)


@dataclass(frozen=True)
class EvaluatedCuttingVariant:
	variant_id: str
	technical_order: int
	result: CuttingResult
	rebuilt_window_start: int | None = None
	rebuilt_window_size: int | None = None


def select_best_cutting_variant(
	candidates: list[EvaluatedCuttingVariant],
	return_remnant_settings: ReturnRemnantSettings | None = None,
	prioritize_return_remnants: bool = True,
) -> CuttingResult:
	if not candidates:
		raise ValueError("Нельзя выбрать результат: не передано ни одного варианта раскладки.")

	effective_return_remnant_settings = (
		return_remnant_settings or ReturnRemnantSettings()
	)
	evaluated = [
		(
			candidate,
			build_cutting_variant_score(
				candidate,
				effective_return_remnant_settings,
				prioritize_return_remnants,
			),
		)
		for candidate in candidates
	]
	selected, score = min(
		evaluated,
		key=lambda item: item[1].selection_key,
	)

	return replace(
		selected.result,
		optimization=OptimizationSummary(
			selected_variant_id=selected.variant_id,
			evaluated_variant_count=len(candidates),
			score=score,
		),
	)


def build_cutting_variant_score(
	candidate: EvaluatedCuttingVariant,
	return_remnant_settings: ReturnRemnantSettings,
	prioritize_return_remnants: bool,
) -> OptimizationVariantScore:
	production_metrics = [
		sheet.production_cut_plan.metrics
		for sheet in candidate.result.sheets
		if sheet.production_cut_plan is not None
	]
	new_material_sheets = [
		sheet
		for sheet in candidate.result.sheets
		if not sheet.sheet_is_remnant
	]
	profile_return_remnants = (
		collect_cutting_result_return_remnants(
			candidate.result,
			return_remnant_settings,
		)
		if prioritize_return_remnants
		else []
	)
	largest_return_remnant = max(
		profile_return_remnants,
		key=lambda remnant: (remnant.area_mm2, remnant.long_side_mm),
		default=None,
	)
	longest_return_remnant = max(
		profile_return_remnants,
		key=lambda remnant: (remnant.long_side_mm, remnant.area_mm2),
		default=None,
	)
	compact_return_remnant = max(
		profile_return_remnants,
		key=lambda remnant: (remnant.short_side_mm**2, remnant.area_mm2),
		default=None,
	)

	return OptimizationVariantScore(
		unplaced_part_count=candidate.result.metrics.unplaced_part_count,
		placed_area_mm2=candidate.result.metrics.placed_area_mm2,
		sheet_count=candidate.result.metrics.sheet_count,
		material_utilization_percent=(
			candidate.result.metrics.material_utilization_percent
		),
		new_sheet_count=len(new_material_sheets),
		new_material_area_mm2=sum(
			sheet.sheet_width_mm * sheet.sheet_height_mm
			for sheet in new_material_sheets
		),
		return_remnant_profile=return_remnant_settings.value_profile,
		return_remnant_area_mm2=sum(
			remnant.area_mm2
			for remnant in profile_return_remnants
		),
		largest_return_remnant_area_mm2=(
			largest_return_remnant.area_mm2
			if largest_return_remnant is not None
			else 0
		),
		longest_return_remnant_side_mm=(
			longest_return_remnant.long_side_mm
			if longest_return_remnant is not None
			else 0
		),
		longest_return_remnant_area_mm2=(
			longest_return_remnant.area_mm2
			if longest_return_remnant is not None
			else 0
		),
		largest_compact_square_area_mm2=(
			compact_return_remnant.short_side_mm**2
			if compact_return_remnant is not None
			else 0
		),
		compact_return_remnant_area_mm2=(
			compact_return_remnant.area_mm2
			if compact_return_remnant is not None
			else 0
		),
		cut_length_mm=sum(metrics.cut_length_mm for metrics in production_metrics),
		pass_count=sum(metrics.pass_count for metrics in production_metrics),
		strip_turn_count=sum(
			metrics.strip_turn_count
			for metrics in production_metrics
		),
		size_setting_count=sum(
			metrics.size_setting_count
			for metrics in production_metrics
		),
		technical_order=candidate.technical_order,
	)
