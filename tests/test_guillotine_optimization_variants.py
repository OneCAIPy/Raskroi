from cutting_app.app.domain.optimization import (
	PartOrdering,
	PlacementHeuristic,
	RotationPreference,
	SheetSelectionHeuristic,
	SplitHeuristic,
)
from cutting_app.app.services.guillotine_optimization_variants import (
	build_default_optimization_variants,
	build_operation_refinement_variants,
)


def test_default_variant_matrix_contains_24_unique_deterministic_combinations() -> None:
	variants = build_default_optimization_variants()

	assert len(variants) == 24
	assert len({variant.variant_id for variant in variants}) == 24
	assert [variant.technical_order for variant in variants] == list(range(24))
	assert all(
		variant.sheet_selection_heuristic == SheetSelectionHeuristic.FIRST_FIT
		for variant in variants
	)


def test_legacy_single_pass_rules_are_the_first_stable_variant() -> None:
	first = build_default_optimization_variants()[0]

	assert first.part_ordering == PartOrdering.AREA_DESC
	assert first.placement_heuristic == PlacementHeuristic.BEST_AREA_FIT
	assert first.split_heuristic == SplitHeuristic.MIN_KERF_LOSS
	assert first.rotation_preference == RotationPreference.UNROTATED_FIRST
	assert first.variant_id == (
		"area_desc__best_area_fit__min_kerf_loss__unrotated_first"
	)


def test_operation_refinement_variants_use_best_fit_on_open_sheets() -> None:
	variants = build_operation_refinement_variants()

	assert len(variants) == 24
	assert len({variant.variant_id for variant in variants}) == 24
	assert [variant.technical_order for variant in variants] == list(range(24, 48))
	assert all(
		variant.sheet_selection_heuristic
		== SheetSelectionHeuristic.BEST_USED_SHEET_FIT
		for variant in variants
	)
	assert all(
		variant.variant_id.endswith("__best_used_sheet_fit")
		for variant in variants
	)
