from cutting_app.app.domain.optimization import (
	OptimizationVariant,
	PartOrdering,
	PlacementHeuristic,
	RotationPreference,
	SheetSelectionHeuristic,
	SplitHeuristic,
)


def build_default_optimization_variants() -> tuple[OptimizationVariant, ...]:
	return _build_optimization_variants(
		sheet_selection_heuristic=SheetSelectionHeuristic.FIRST_FIT,
		technical_order_start=0,
	)


def build_operation_refinement_variants() -> tuple[OptimizationVariant, ...]:
	return _build_optimization_variants(
		sheet_selection_heuristic=SheetSelectionHeuristic.BEST_USED_SHEET_FIT,
		technical_order_start=len(build_default_optimization_variants()),
	)


def _build_optimization_variants(
	sheet_selection_heuristic: SheetSelectionHeuristic,
	technical_order_start: int,
) -> tuple[OptimizationVariant, ...]:
	variants: list[OptimizationVariant] = []

	for part_ordering in PartOrdering:
		for placement_heuristic in PlacementHeuristic:
			for split_heuristic in SplitHeuristic:
				for rotation_preference in RotationPreference:
					technical_order = technical_order_start + len(variants)
					variants.append(
						OptimizationVariant(
							variant_id=_make_variant_id(
								part_ordering=part_ordering,
								placement_heuristic=placement_heuristic,
								split_heuristic=split_heuristic,
								rotation_preference=rotation_preference,
								sheet_selection_heuristic=sheet_selection_heuristic,
							),
							technical_order=technical_order,
							part_ordering=part_ordering,
							placement_heuristic=placement_heuristic,
							split_heuristic=split_heuristic,
							rotation_preference=rotation_preference,
							sheet_selection_heuristic=sheet_selection_heuristic,
						)
					)

	return tuple(variants)


def _make_variant_id(
	part_ordering: PartOrdering,
	placement_heuristic: PlacementHeuristic,
	split_heuristic: SplitHeuristic,
	rotation_preference: RotationPreference,
	sheet_selection_heuristic: SheetSelectionHeuristic,
) -> str:
	parts = [
		part_ordering.value,
		placement_heuristic.value,
		split_heuristic.value,
		rotation_preference.value,
	]
	if sheet_selection_heuristic != SheetSelectionHeuristic.FIRST_FIT:
		parts.append(sheet_selection_heuristic.value)
	return "__".join(parts)
