from collections import Counter
from dataclasses import dataclass, replace

from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.return_remnant import (
	ReturnRemnantProfile,
	ReturnRemnantSettings,
)
from cutting_app.app.services.cutting_result_assembler import (
	assemble_cutting_result,
)
from cutting_app.app.services.cutting_variant_selector import (
	EvaluatedCuttingVariant,
	build_cutting_variant_score,
)


_MIN_SHEETS = 4
_OPTIONS_PER_OBJECTIVE = 1
_BEAM_PER_OBJECTIVE = 4


@dataclass(frozen=True)
class _WindowPatch:
	start: int
	end: int
	candidate: EvaluatedCuttingVariant


def build_multi_window_combination_candidates(
	seed_result: CuttingResult,
	window_candidates: list[EvaluatedCuttingVariant],
	return_remnant_settings: ReturnRemnantSettings,
	technical_order_start: int,
) -> list[EvaluatedCuttingVariant]:
	if seed_result.unplaced_parts or len(seed_result.sheets) < _MIN_SHEETS:
		return []

	patches_by_start = _select_patch_options(
		seed_result=seed_result,
		window_candidates=window_candidates,
		return_remnant_settings=return_remnant_settings,
	)
	if not patches_by_start:
		return []

	states_by_cursor: dict[int, list[tuple[_WindowPatch, ...]]] = {0: [()]}
	result_cache: dict[tuple[tuple[int, int, str], ...], CuttingResult] = {}
	sheet_count = len(seed_result.sheets)

	for cursor in range(sheet_count):
		current_states = _prune_states(
			states=states_by_cursor.get(cursor, []),
			seed_result=seed_result,
			return_remnant_settings=return_remnant_settings,
			result_cache=result_cache,
		)
		if not current_states:
			continue
		states_by_cursor.setdefault(cursor + 1, []).extend(current_states)
		for patch in patches_by_start.get(cursor, []):
			states_by_cursor.setdefault(patch.end, []).extend(
				state + (patch,)
				for state in current_states
			)

	final_states = _prune_states(
		states=states_by_cursor.get(sheet_count, []),
		seed_result=seed_result,
		return_remnant_settings=return_remnant_settings,
		result_cache=result_cache,
	)
	combined_states = [state for state in final_states if len(state) >= 2]
	combined_candidates = [
		EvaluatedCuttingVariant(
			variant_id=_make_variant_id(state),
			technical_order=technical_order_start + state_index,
			result=_build_result(
				seed_result=seed_result,
				state=state,
				result_cache=result_cache,
			),
		)
		for state_index, state in enumerate(combined_states)
	]
	return _select_useful_combined_candidates(
		seed_result=seed_result,
		window_candidates=window_candidates,
		combined_candidates=combined_candidates,
		return_remnant_settings=return_remnant_settings,
	)


def _select_useful_combined_candidates(
	seed_result: CuttingResult,
	window_candidates: list[EvaluatedCuttingVariant],
	combined_candidates: list[EvaluatedCuttingVariant],
	return_remnant_settings: ReturnRemnantSettings,
) -> list[EvaluatedCuttingVariant]:
	if not combined_candidates:
		return []

	existing_candidates = [
		EvaluatedCuttingVariant(
			variant_id="multi_window_seed",
			technical_order=-1,
			result=seed_result,
		),
		*window_candidates,
	]
	selected: list[EvaluatedCuttingVariant] = []
	for objective_setting in _build_objective_settings(return_remnant_settings):
		best_existing = min(
			existing_candidates,
			key=lambda candidate: build_cutting_variant_score(
				candidate,
				objective_setting,
				prioritize_return_remnants=True,
			).selection_key,
		)
		best_combined = min(
			combined_candidates,
			key=lambda candidate: build_cutting_variant_score(
				candidate,
				objective_setting,
				prioritize_return_remnants=True,
			).selection_key,
		)
		if build_cutting_variant_score(
			best_combined,
			objective_setting,
			prioritize_return_remnants=True,
		).selection_key < build_cutting_variant_score(
			best_existing,
			objective_setting,
			prioritize_return_remnants=True,
		).selection_key:
			selected.append(best_combined)

	best_existing_operations = min(
		existing_candidates,
		key=lambda candidate: build_cutting_variant_score(
			candidate,
			return_remnant_settings,
			prioritize_return_remnants=False,
		).selection_key,
	)
	best_combined_operations = min(
		combined_candidates,
		key=lambda candidate: build_cutting_variant_score(
			candidate,
			return_remnant_settings,
			prioritize_return_remnants=False,
		).selection_key,
	)
	if build_cutting_variant_score(
		best_combined_operations,
		return_remnant_settings,
		prioritize_return_remnants=False,
	).selection_key < build_cutting_variant_score(
		best_existing_operations,
		return_remnant_settings,
		prioritize_return_remnants=False,
	).selection_key:
		selected.append(best_combined_operations)

	result: list[EvaluatedCuttingVariant] = []
	seen_variant_ids: set[str] = set()
	for candidate in selected:
		if candidate.variant_id in seen_variant_ids:
			continue
		seen_variant_ids.add(candidate.variant_id)
		result.append(candidate)
	return result


def _select_patch_options(
	seed_result: CuttingResult,
	window_candidates: list[EvaluatedCuttingVariant],
	return_remnant_settings: ReturnRemnantSettings,
) -> dict[int, list[_WindowPatch]]:
	candidates_by_window: dict[tuple[int, int], list[EvaluatedCuttingVariant]] = {}
	for candidate in window_candidates:
		start = candidate.rebuilt_window_start
		size = candidate.rebuilt_window_size
		if start is None or size is None:
			continue
		end = start + size
		if not _is_valid_patch(seed_result, candidate.result, start, end):
			continue
		candidates_by_window.setdefault((start, end), []).append(candidate)

	objective_settings = _build_objective_settings(return_remnant_settings)
	patches_by_start: dict[int, list[_WindowPatch]] = {}
	for (start, end), candidates in candidates_by_window.items():
		selected: list[EvaluatedCuttingVariant] = []
		for objective_setting in objective_settings:
			selected.extend(
				sorted(
					candidates,
					key=lambda candidate: build_cutting_variant_score(
						candidate,
						objective_setting,
						prioritize_return_remnants=True,
					).selection_key,
				)[:_OPTIONS_PER_OBJECTIVE]
			)
		selected.extend(
			sorted(
				candidates,
				key=lambda candidate: build_cutting_variant_score(
					candidate,
					return_remnant_settings,
					prioritize_return_remnants=False,
				).selection_key,
			)[:_OPTIONS_PER_OBJECTIVE]
		)

		seen_variant_ids: set[str] = set()
		for candidate in selected:
			if candidate.variant_id in seen_variant_ids:
				continue
			seen_variant_ids.add(candidate.variant_id)
			patches_by_start.setdefault(start, []).append(
				_WindowPatch(start=start, end=end, candidate=candidate)
			)

	for patches in patches_by_start.values():
		patches.sort(
			key=lambda patch: (
				patch.end,
				patch.candidate.technical_order,
				patch.candidate.variant_id,
			)
		)
	return patches_by_start


def _is_valid_patch(
	seed_result: CuttingResult,
	candidate_result: CuttingResult,
	start: int,
	end: int,
) -> bool:
	if candidate_result.unplaced_parts:
		return False
	if len(candidate_result.sheets) != len(seed_result.sheets):
		return False
	if start < 0 or end > len(seed_result.sheets) or start >= end:
		return False
	for seed_sheet, candidate_sheet in zip(
		seed_result.sheets[start:end],
		candidate_result.sheets[start:end],
		strict=True,
	):
		if (
			seed_sheet.sheet_name != candidate_sheet.sheet_name
			or seed_sheet.sheet_stock_name != candidate_sheet.sheet_stock_name
			or seed_sheet.sheet_is_remnant != candidate_sheet.sheet_is_remnant
			or seed_sheet.sheet_width_mm != candidate_sheet.sheet_width_mm
			or seed_sheet.sheet_height_mm != candidate_sheet.sheet_height_mm
		):
			return False
	seed_parts = Counter(
		part.part_number
		for sheet in seed_result.sheets[start:end]
		for part in sheet.placed_parts
	)
	candidate_parts = Counter(
		part.part_number
		for sheet in candidate_result.sheets[start:end]
		for part in sheet.placed_parts
	)
	return seed_parts == candidate_parts


def _build_objective_settings(
	return_remnant_settings: ReturnRemnantSettings,
) -> tuple[ReturnRemnantSettings, ...]:
	return tuple(
		replace(return_remnant_settings, value_profile=profile)
		for profile in ReturnRemnantProfile
	)


def _prune_states(
	states: list[tuple[_WindowPatch, ...]],
	seed_result: CuttingResult,
	return_remnant_settings: ReturnRemnantSettings,
	result_cache: dict[tuple[tuple[int, int, str], ...], CuttingResult],
) -> list[tuple[_WindowPatch, ...]]:
	unique_states: list[tuple[_WindowPatch, ...]] = []
	seen_keys: set[tuple[tuple[int, int, str], ...]] = set()
	for state in states:
		state_key = _state_key(state)
		if state_key in seen_keys:
			continue
		seen_keys.add(state_key)
		unique_states.append(state)

	selected: list[tuple[_WindowPatch, ...]] = []
	for objective_setting in _build_objective_settings(return_remnant_settings):
		selected.extend(
			sorted(
				unique_states,
				key=lambda state: _score_state(
					state=state,
					seed_result=seed_result,
					return_remnant_settings=objective_setting,
					prioritize_return_remnants=True,
					result_cache=result_cache,
				),
			)[:_BEAM_PER_OBJECTIVE]
		)
	selected.extend(
		sorted(
			unique_states,
			key=lambda state: _score_state(
				state=state,
				seed_result=seed_result,
				return_remnant_settings=return_remnant_settings,
				prioritize_return_remnants=False,
				result_cache=result_cache,
			),
		)[:_BEAM_PER_OBJECTIVE]
	)

	result: list[tuple[_WindowPatch, ...]] = []
	seen_keys.clear()
	for state in selected:
		state_key = _state_key(state)
		if state_key in seen_keys:
			continue
		seen_keys.add(state_key)
		result.append(state)
	return result


def _score_state(
	state: tuple[_WindowPatch, ...],
	seed_result: CuttingResult,
	return_remnant_settings: ReturnRemnantSettings,
	prioritize_return_remnants: bool,
	result_cache: dict[tuple[tuple[int, int, str], ...], CuttingResult],
) -> tuple[float | int, ...]:
	return build_cutting_variant_score(
		EvaluatedCuttingVariant(
			variant_id="multi_window_state",
			technical_order=0,
			result=_build_result(
				seed_result=seed_result,
				state=state,
				result_cache=result_cache,
			),
		),
		return_remnant_settings,
		prioritize_return_remnants=prioritize_return_remnants,
	).selection_key


def _build_result(
	seed_result: CuttingResult,
	state: tuple[_WindowPatch, ...],
	result_cache: dict[tuple[tuple[int, int, str], ...], CuttingResult],
) -> CuttingResult:
	state_key = _state_key(state)
	cached = result_cache.get(state_key)
	if cached is not None:
		return cached

	sheets = list(seed_result.sheets)
	for patch in state:
		sheets[patch.start:patch.end] = patch.candidate.result.sheets[
			patch.start:patch.end
		]
	result = assemble_cutting_result(sheets)
	result_cache[state_key] = result
	return result


def _state_key(
	state: tuple[_WindowPatch, ...],
) -> tuple[tuple[int, int, str], ...]:
	return tuple(
		(patch.start, patch.end, patch.candidate.variant_id)
		for patch in state
	)


def _make_variant_id(state: tuple[_WindowPatch, ...]) -> str:
	window_ids = "_".join(
		f"{patch.start + 1}_to_{patch.end}"
		for patch in state
	)
	rebuild_ids = "+".join(
		patch.candidate.variant_id.rsplit("__rebuild_", maxsplit=1)[-1]
		for patch in state
	)
	return f"multi_windows_{window_ids}__rebuild_{rebuild_ids}"
