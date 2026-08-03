from cutting_app.app.domain.optimization import (
	OptimizationVariant,
	PartOrdering,
	PlacementHeuristic,
	RotationPreference,
	SplitHeuristic,
)


def build_default_optimization_variants() -> tuple[OptimizationVariant, ...]:
	variants: list[OptimizationVariant] = []

	for part_ordering in PartOrdering:
		for placement_heuristic in PlacementHeuristic:
			for split_heuristic in SplitHeuristic:
				for rotation_preference in RotationPreference:
					technical_order = len(variants)
					variants.append(
						OptimizationVariant(
							variant_id=_make_variant_id(
								part_ordering=part_ordering,
								placement_heuristic=placement_heuristic,
								split_heuristic=split_heuristic,
								rotation_preference=rotation_preference,
							),
							technical_order=technical_order,
							part_ordering=part_ordering,
							placement_heuristic=placement_heuristic,
							split_heuristic=split_heuristic,
							rotation_preference=rotation_preference,
						)
					)

	return tuple(variants)


def _make_variant_id(
	part_ordering: PartOrdering,
	placement_heuristic: PlacementHeuristic,
	split_heuristic: SplitHeuristic,
	rotation_preference: RotationPreference,
) -> str:
	return "__".join(
		(
			part_ordering.value,
			placement_heuristic.value,
			split_heuristic.value,
			rotation_preference.value,
		)
	)
