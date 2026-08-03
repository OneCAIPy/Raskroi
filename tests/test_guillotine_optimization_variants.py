from cutting_app.app.domain.optimization import (
	PartOrdering,
	PlacementHeuristic,
	RotationPreference,
	SplitHeuristic,
)
from cutting_app.app.services.guillotine_optimization_variants import (
	build_default_optimization_variants,
)


def test_default_variant_matrix_contains_24_unique_deterministic_combinations() -> None:
	variants = build_default_optimization_variants()

	assert len(variants) == 24
	assert len({variant.variant_id for variant in variants}) == 24
	assert [variant.technical_order for variant in variants] == list(range(24))


def test_legacy_single_pass_rules_are_the_first_stable_variant() -> None:
	first = build_default_optimization_variants()[0]

	assert first.part_ordering == PartOrdering.AREA_DESC
	assert first.placement_heuristic == PlacementHeuristic.BEST_AREA_FIT
	assert first.split_heuristic == SplitHeuristic.MIN_KERF_LOSS
	assert first.rotation_preference == RotationPreference.UNROTATED_FIRST
	assert first.variant_id == (
		"area_desc__best_area_fit__min_kerf_loss__unrotated_first"
	)
