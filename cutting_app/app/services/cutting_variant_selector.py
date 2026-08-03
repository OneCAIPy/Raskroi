from dataclasses import dataclass, replace

from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.optimization import (
	OptimizationSummary,
	OptimizationVariantScore,
)


@dataclass(frozen=True)
class EvaluatedCuttingVariant:
	variant_id: str
	technical_order: int
	result: CuttingResult


def select_best_cutting_variant(
	candidates: list[EvaluatedCuttingVariant],
) -> CuttingResult:
	if not candidates:
		raise ValueError("Нельзя выбрать результат: не передано ни одного варианта раскладки.")

	evaluated = [
		(candidate, _build_variant_score(candidate))
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


def _build_variant_score(
	candidate: EvaluatedCuttingVariant,
) -> OptimizationVariantScore:
	production_metrics = [
		sheet.production_cut_plan.metrics
		for sheet in candidate.result.sheets
		if sheet.production_cut_plan is not None
	]

	return OptimizationVariantScore(
		unplaced_part_count=candidate.result.metrics.unplaced_part_count,
		placed_area_mm2=candidate.result.metrics.placed_area_mm2,
		sheet_count=candidate.result.metrics.sheet_count,
		material_utilization_percent=(
			candidate.result.metrics.material_utilization_percent
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
