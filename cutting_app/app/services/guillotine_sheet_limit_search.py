from copy import deepcopy
from dataclasses import dataclass

from cutting_app.app.domain.cutting_result import CuttingResult, UnplacedPart
from cutting_app.app.domain.optimization import OptimizationVariant
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.domain.return_remnant import ReturnRemnantSettings
from cutting_app.app.domain.sheet import SheetInput
from cutting_app.app.domain.sheet_limit_search import (
	SheetLimitSearchReport,
	SheetLimitSearchSettings,
	SheetLimitSearchStatus,
)
from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.services.cutting_variant_selector import (
	EvaluatedCuttingVariant,
	select_best_cutting_variant,
)
from cutting_app.app.services.cutting_result_assembler import (
	assemble_cutting_result,
)
from cutting_app.app.services.guillotine_optimization_variants import (
	build_default_optimization_variants,
)
import cutting_app.app.services.guillotine_optimizer as optimizer


@dataclass(frozen=True)
class _PlacementOption:
	sheet_index: int
	free_node_index: int
	rotation: Rotation
	width_mm: float
	height_mm: float
	split_strategy: optimizer.SplitStrategy
	opens_sheet: bool
	is_alternate_split: bool
	rank_key: tuple[float | int | str, ...]


@dataclass(frozen=True)
class _PartShape:
	part_unit: optimizer._PartUnit
	width_mm: float
	height_mm: float
	rotated_width_mm: float | None
	rotated_height_mm: float | None
	area_mm2: float

	@property
	def orientations(self) -> tuple[tuple[Rotation, float, float], ...]:
		orientations = [(Rotation.DEG_0, self.width_mm, self.height_mm)]
		if self.rotated_width_mm is not None and self.rotated_height_mm is not None:
			orientations.append(
				(Rotation.DEG_90, self.rotated_width_mm, self.rotated_height_mm)
			)
		return tuple(orientations)


@dataclass(frozen=True)
class _SearchState:
	working_sheets: tuple[optimizer._WorkingSheet, ...]
	placed_part_count: int = 0
	placed_area_mm2: float = 0


@dataclass(frozen=True)
class _VariantSearchOutcome:
	complete_states: tuple[_SearchState, ...]
	best_partial_state: _SearchState
	evaluated_state_count: int
	pruned_state_count: int
	remaining_part_units: tuple[optimizer._PartUnit, ...]


def search_guillotine_sheet_limit(
	parts: list[PartInput],
	sheets: list[SheetInput],
	settings: CutSettings,
	search_settings: SheetLimitSearchSettings,
	return_remnant_settings: ReturnRemnantSettings | None = None,
) -> SheetLimitSearchReport:
	working_sheets = tuple(optimizer._create_working_sheets(sheets))
	if len(working_sheets) < search_settings.sheet_limit:
		raise ValueError("В наличии меньше листов, чем заданный лимит поиска.")

	part_units = optimizer._expand_parts(parts)
	part_area_mm2 = sum(_build_part_shape(part_unit).area_mm2 for part_unit in part_units)
	maximum_working_area_mm2 = sum(
		sorted(
			(sheet.root.area.width_mm * sheet.root.area.height_mm for sheet in working_sheets),
			reverse=True,
		)[:search_settings.sheet_limit]
	)
	if part_area_mm2 > maximum_working_area_mm2:
		return SheetLimitSearchReport(
			status=SheetLimitSearchStatus.PROVEN_IMPOSSIBLE_BY_AREA,
			settings=search_settings,
			evaluated_variant_count=0,
			evaluated_state_count=0,
			pruned_state_count=0,
			best_placed_part_count=0,
			best_placed_area_mm2=0,
			deepest_search_prefix_part_count=0,
			deepest_search_prefix_area_mm2=0,
		)

	variants = build_default_optimization_variants()[:search_settings.max_variants]
	greedy_candidates = [
		EvaluatedCuttingVariant(
			variant_id=f"hard_limit_greedy__{variant.variant_id}",
			technical_order=variant.technical_order,
			result=optimizer._optimize_part_units_variant(
				part_units=optimizer._expand_parts(parts),
				working_sheets=optimizer._create_working_sheets(sheets)[
					:search_settings.sheet_limit
				],
				settings=settings,
				variant=variant,
			),
		)
		for variant in variants
	]
	best_greedy_result = select_best_cutting_variant(
		greedy_candidates,
		return_remnant_settings=return_remnant_settings,
		prioritize_return_remnants=False,
	)
	if not best_greedy_result.unplaced_parts:
		return SheetLimitSearchReport(
			status=SheetLimitSearchStatus.FOUND,
			settings=search_settings,
			evaluated_variant_count=len(variants),
			evaluated_state_count=0,
			pruned_state_count=0,
			best_placed_part_count=best_greedy_result.metrics.placed_part_count,
			best_placed_area_mm2=best_greedy_result.metrics.placed_area_mm2,
			deepest_search_prefix_part_count=best_greedy_result.metrics.placed_part_count,
			deepest_search_prefix_area_mm2=best_greedy_result.metrics.placed_area_mm2,
			result=best_greedy_result,
			best_partial_result=best_greedy_result,
		)
	outcomes = [
		_search_variant(
			part_units=part_units,
			working_sheets=working_sheets,
			settings=settings,
			search_settings=search_settings,
			variant=variant,
		)
		for variant in variants
	]
	complete_candidates: list[EvaluatedCuttingVariant] = []
	for variant, outcome in zip(variants, outcomes, strict=True):
		for state_index, state in enumerate(outcome.complete_states):
			complete_candidates.append(
				EvaluatedCuttingVariant(
					variant_id=(
						f"hard_limit_{search_settings.sheet_limit}"
						f"__{variant.variant_id}__beam_{state_index}"
					),
					technical_order=len(complete_candidates),
					result=_state_to_cutting_result(
						state=state,
						settings=settings,
						remaining_part_units=(),
					),
				)
			)

	evaluated_state_count = sum(outcome.evaluated_state_count for outcome in outcomes)
	pruned_state_count = sum(outcome.pruned_state_count for outcome in outcomes)
	best_outcome = max(
		outcomes,
		key=lambda outcome: _partial_state_selection_key(outcome.best_partial_state),
	)
	best_beam_partial_result = _state_to_cutting_result(
		state=best_outcome.best_partial_state,
		settings=settings,
		remaining_part_units=best_outcome.remaining_part_units,
	)
	best_partial_result = max(
		(best_greedy_result, best_beam_partial_result),
		key=lambda result: (
			result.metrics.placed_part_count,
			result.metrics.placed_area_mm2,
		),
	)

	if complete_candidates:
		result = select_best_cutting_variant(
			complete_candidates,
			return_remnant_settings=return_remnant_settings,
		)
		return SheetLimitSearchReport(
			status=SheetLimitSearchStatus.FOUND,
			settings=search_settings,
			evaluated_variant_count=len(variants),
			evaluated_state_count=evaluated_state_count,
			pruned_state_count=pruned_state_count,
			best_placed_part_count=result.metrics.placed_part_count,
			best_placed_area_mm2=result.metrics.placed_area_mm2,
			deepest_search_prefix_part_count=(
				best_outcome.best_partial_state.placed_part_count
			),
			deepest_search_prefix_area_mm2=(
				best_outcome.best_partial_state.placed_area_mm2
			),
			result=result,
			best_partial_result=result,
		)

	return SheetLimitSearchReport(
		status=SheetLimitSearchStatus.NOT_FOUND_WITHIN_BUDGET,
		settings=search_settings,
		evaluated_variant_count=len(variants),
		evaluated_state_count=evaluated_state_count,
		pruned_state_count=pruned_state_count,
		best_placed_part_count=best_partial_result.metrics.placed_part_count,
		best_placed_area_mm2=best_partial_result.metrics.placed_area_mm2,
		deepest_search_prefix_part_count=(
			best_outcome.best_partial_state.placed_part_count
		),
		deepest_search_prefix_area_mm2=(
			best_outcome.best_partial_state.placed_area_mm2
		),
		best_partial_result=best_partial_result,
	)


def _search_variant(
	part_units: list[optimizer._PartUnit],
	working_sheets: tuple[optimizer._WorkingSheet, ...],
	settings: CutSettings,
	search_settings: SheetLimitSearchSettings,
	variant: OptimizationVariant,
) -> _VariantSearchOutcome:
	ordered_part_units = optimizer._sort_part_units(part_units, variant.part_ordering)
	ordered_part_shapes = [
		_build_part_shape(part_unit)
		for part_unit in ordered_part_units
	]
	suffix_area_mm2 = _build_suffix_areas(ordered_part_shapes)
	unique_remaining_shapes = _build_unique_remaining_shapes(ordered_part_shapes)
	states = [_SearchState(working_sheets=working_sheets)]
	best_partial_state = states[0]
	evaluated_state_count = 0
	pruned_state_count = 0
	remaining_part_units: tuple[optimizer._PartUnit, ...] = tuple(ordered_part_units)

	for part_index, part_shape in enumerate(ordered_part_shapes):
		part_unit = part_shape.part_unit
		children: list[_SearchState] = []
		for state in states:
			options = _build_placement_options(
				state=state,
				part_shape=part_shape,
				settings=settings,
				search_settings=search_settings,
				variant=variant,
			)
			for option in _select_diverse_options(options, search_settings.branch_factor):
				child = _place_option(
					state=state,
					part_unit=part_unit,
					option=option,
					settings=settings,
				)
				evaluated_state_count += 1
				if _state_can_fit_remaining(
					state=child,
					remaining_area_mm2=suffix_area_mm2[part_index + 1],
					remaining_shapes=unique_remaining_shapes[part_index + 1],
					sheet_limit=search_settings.sheet_limit,
				):
					children.append(child)
				if _partial_state_selection_key(child) > _partial_state_selection_key(
					best_partial_state
				):
					best_partial_state = child

		if not children:
			remaining_part_units = tuple(ordered_part_units[part_index:])
			break

		states, pruned = _prune_states(
			states=children,
			remaining_shapes=unique_remaining_shapes[part_index + 1],
			beam_width=search_settings.beam_width,
			sheet_limit=search_settings.sheet_limit,
		)
		pruned_state_count += pruned
		best_in_beam = max(states, key=_partial_state_selection_key)
		if _partial_state_selection_key(best_in_beam) > _partial_state_selection_key(
			best_partial_state
		):
			best_partial_state = best_in_beam
		remaining_part_units = tuple(ordered_part_units[part_index + 1:])
	else:
		remaining_part_units = ()

	remaining_part_units = tuple(
		ordered_part_units[best_partial_state.placed_part_count:]
	)
	complete_states = (
		tuple(states)
		if best_partial_state.placed_part_count == len(ordered_part_units)
		else ()
	)
	return _VariantSearchOutcome(
		complete_states=complete_states,
		best_partial_state=best_partial_state,
		evaluated_state_count=evaluated_state_count,
		pruned_state_count=pruned_state_count,
		remaining_part_units=remaining_part_units,
	)


def _build_placement_options(
	state: _SearchState,
	part_shape: _PartShape,
	settings: CutSettings,
	search_settings: SheetLimitSearchSettings,
	variant: OptimizationVariant,
) -> list[_PlacementOption]:
	used_sheet_count = _used_sheet_count(state)
	seen_sheet_states: set[tuple[object, ...]] = set()
	options: list[_PlacementOption] = []

	for sheet_index, working_sheet in enumerate(state.working_sheets):
		opens_sheet = not working_sheet.placed_parts
		if opens_sheet and used_sheet_count >= search_settings.sheet_limit:
			continue
		sheet_state = _working_sheet_capacity_signature(working_sheet)
		if sheet_state in seen_sheet_states:
			continue
		seen_sheet_states.add(sheet_state)

		for free_node_index, free_node in enumerate(working_sheet.free_nodes):
			for rotation, width_mm, height_mm in part_shape.orientations:
				if not optimizer._fits(
					free_node.node.area,
					width_mm,
					height_mm,
				):
					continue
				preferred_split = optimizer._select_split_strategy(
					area=free_node.node.area,
					part_width_mm=width_mm,
					part_height_mm=height_mm,
					kerf_width_mm=settings.kerf_width_mm,
					split_heuristic=variant.split_heuristic,
				)
				for split_strategy in optimizer.SplitStrategy:
					candidate = optimizer._PlacementCandidate(
						free_node=free_node,
						rotation=rotation,
						width_mm=width_mm,
						height_mm=height_mm,
						split_strategy=split_strategy,
					)
					placement_key = optimizer._score_placement_candidate(
						candidate,
						settings.kerf_width_mm,
						variant.placement_heuristic,
						variant.rotation_preference,
					)
					is_alternate_split = split_strategy != preferred_split
					options.append(
						_PlacementOption(
							sheet_index=sheet_index,
							free_node_index=free_node_index,
							rotation=rotation,
							width_mm=width_mm,
							height_mm=height_mm,
							split_strategy=split_strategy,
							opens_sheet=opens_sheet,
							is_alternate_split=is_alternate_split,
							rank_key=(
								*optimizer._sheet_priority_key(working_sheet.sheet),
								1 if opens_sheet else 0,
								*placement_key[:3],
								1 if is_alternate_split else 0,
								*placement_key[3:],
								sheet_index,
								free_node_index,
								rotation.value,
								split_strategy.value,
							),
						)
					)

	return sorted(options, key=lambda option: option.rank_key)


def _select_diverse_options(
	options: list[_PlacementOption],
	branch_factor: int,
) -> list[_PlacementOption]:
	if branch_factor == 1:
		return options[:1]

	selected = list(options[:branch_factor])
	for predicate in (
		lambda option: option.opens_sheet,
		lambda option: option.rotation == Rotation.DEG_90,
		lambda option: option.is_alternate_split,
	):
		diverse = next((option for option in options if predicate(option)), None)
		if diverse is None or diverse in selected:
			continue
		if len(selected) < branch_factor:
			selected.append(diverse)
		else:
			selected[-1] = diverse
		selected = sorted(set(selected), key=lambda option: option.rank_key)
	return selected


def _place_option(
	state: _SearchState,
	part_unit: optimizer._PartUnit,
	option: _PlacementOption,
	settings: CutSettings,
) -> _SearchState:
	working_sheets = list(state.working_sheets)
	working_sheet = deepcopy(working_sheets[option.sheet_index])
	free_node = working_sheet.free_nodes[option.free_node_index]
	candidate = optimizer._PlacementCandidate(
		free_node=free_node,
		rotation=option.rotation,
		width_mm=option.width_mm,
		height_mm=option.height_mm,
		split_strategy=option.split_strategy,
	)
	optimizer._place_candidate(
		working_sheet=working_sheet,
		part_unit=part_unit,
		candidate=candidate,
		settings=settings,
	)
	working_sheets[option.sheet_index] = working_sheet
	return _SearchState(
		working_sheets=tuple(working_sheets),
		placed_part_count=state.placed_part_count + 1,
		placed_area_mm2=state.placed_area_mm2 + option.width_mm * option.height_mm,
	)


def _state_can_fit_remaining(
	state: _SearchState,
	remaining_area_mm2: float,
	remaining_shapes: tuple[_PartShape, ...],
	sheet_limit: int,
) -> bool:
	if not remaining_shapes:
		return True
	capacity_areas = _available_free_areas(state, sheet_limit)
	if remaining_area_mm2 > sum(area.width_mm * area.height_mm for area in capacity_areas):
		return False
	fit_areas = _all_potential_free_areas(state)

	return all(
		_any_area_fits_shape(fit_areas, shape)
		for shape in remaining_shapes
	)


def _prune_states(
	states: list[_SearchState],
	remaining_shapes: tuple[_PartShape, ...],
	beam_width: int,
	sheet_limit: int,
) -> tuple[list[_SearchState], int]:
	unique_by_capacity: dict[tuple[object, ...], _SearchState] = {}
	for state in states:
		unique_by_capacity.setdefault(_state_capacity_signature(state), state)
	unique_states = list(unique_by_capacity.values())
	ordered = sorted(
		unique_states,
		key=lambda state: _state_search_key(
			state=state,
			remaining_shapes=remaining_shapes,
			sheet_limit=sheet_limit,
		),
	)
	kept = ordered[:beam_width]
	return kept, len(states) - len(kept)


def _state_search_key(
	state: _SearchState,
	remaining_shapes: tuple[_PartShape, ...],
	sheet_limit: int,
) -> tuple[float | int, ...]:
	available_areas = _available_free_areas(state, sheet_limit)
	sampled_shapes = _sample_shapes(remaining_shapes, maximum_count=12)
	dead_area_mm2 = sum(
		area.width_mm * area.height_mm
		for area in available_areas
		if not any(
			_area_fits_shape(area, shape)
			for shape in sampled_shapes
		)
	)
	fit_counts = [
		sum(_area_fits_shape(area, shape) for area in available_areas)
		for shape in sampled_shapes
	]
	return (
		dead_area_mm2,
		-sum(min(count, 12) for count in fit_counts),
		-sum(area.width_mm * area.height_mm for area in available_areas),
		_used_sheet_count(state),
		len(available_areas),
	)


def _available_free_areas(
	state: _SearchState,
	sheet_limit: int,
) -> list[optimizer.RectArea]:
	used_sheets = [sheet for sheet in state.working_sheets if sheet.placed_parts]
	unused_sheets = [sheet for sheet in state.working_sheets if not sheet.placed_parts]
	remaining_sheet_count = sheet_limit - len(used_sheets)
	selected_unused_sheets = sorted(
		unused_sheets,
		key=lambda sheet: sheet.root.area.width_mm * sheet.root.area.height_mm,
		reverse=True,
	)[:remaining_sheet_count]
	return [
		free_node.node.area
		for sheet in [*used_sheets, *selected_unused_sheets]
		for free_node in sheet.free_nodes
	]


def _all_potential_free_areas(state: _SearchState) -> list[optimizer.RectArea]:
	return [
		free_node.node.area
		for sheet in state.working_sheets
		for free_node in sheet.free_nodes
	]


def _any_area_fits_shape(
	areas: list[optimizer.RectArea],
	shape: _PartShape,
) -> bool:
	return any(_area_fits_shape(area, shape) for area in areas)


def _area_fits_shape(area: optimizer.RectArea, shape: _PartShape) -> bool:
	for _, width_mm, height_mm in shape.orientations:
		if optimizer._fits(area, width_mm, height_mm):
			return True
	return False


def _build_part_shape(part_unit: optimizer._PartUnit) -> _PartShape:
	part_sizes = optimizer.calculate_part_sizes(part_unit.part)
	rotated_width_mm = None
	rotated_height_mm = None
	if part_unit.part.rotation_allowed:
		rotated = optimizer.calculate_placed_dimensions(part_sizes, Rotation.DEG_90)
		rotated_width_mm = rotated.width_mm
		rotated_height_mm = rotated.height_mm
	return _PartShape(
		part_unit=part_unit,
		width_mm=part_sizes.cutting_l_mm,
		height_mm=part_sizes.cutting_w_mm,
		rotated_width_mm=rotated_width_mm,
		rotated_height_mm=rotated_height_mm,
		area_mm2=part_sizes.cutting_l_mm * part_sizes.cutting_w_mm,
	)


def _build_suffix_areas(part_shapes: list[_PartShape]) -> list[float]:
	suffix_areas = [0.0] * (len(part_shapes) + 1)
	for index in range(len(part_shapes) - 1, -1, -1):
		suffix_areas[index] = suffix_areas[index + 1] + part_shapes[index].area_mm2
	return suffix_areas


def _build_unique_remaining_shapes(
	part_shapes: list[_PartShape],
) -> list[tuple[_PartShape, ...]]:
	remaining: list[tuple[_PartShape, ...]] = [()] * (len(part_shapes) + 1)
	unique_by_dimensions: dict[tuple[float | None, ...], _PartShape] = {}
	for index in range(len(part_shapes) - 1, -1, -1):
		shape = part_shapes[index]
		key = (
			shape.width_mm,
			shape.height_mm,
			shape.rotated_width_mm,
			shape.rotated_height_mm,
		)
		unique_by_dimensions.setdefault(key, shape)
		remaining[index] = tuple(unique_by_dimensions.values())
	return remaining


def _sample_shapes(
	shapes: tuple[_PartShape, ...],
	maximum_count: int,
) -> tuple[_PartShape, ...]:
	if len(shapes) <= maximum_count:
		return shapes
	step = max(1, len(shapes) // maximum_count)
	sampled = list(shapes[::step][:maximum_count - 1])
	sampled.append(shapes[-1])
	return tuple(sampled)


def _used_sheet_count(state: _SearchState) -> int:
	return sum(bool(sheet.placed_parts) for sheet in state.working_sheets)


def _working_sheet_capacity_signature(
	working_sheet: optimizer._WorkingSheet,
) -> tuple[object, ...]:
	return (
		working_sheet.sheet.name,
		working_sheet.sheet.width_mm,
		working_sheet.sheet.height_mm,
		working_sheet.sheet.is_remnant,
		bool(working_sheet.placed_parts),
		tuple(
			sorted(
				(
					free_node.node.area.width_mm,
					free_node.node.area.height_mm,
				)
				for free_node in working_sheet.free_nodes
			)
		),
	)


def _state_capacity_signature(state: _SearchState) -> tuple[object, ...]:
	return tuple(
		sorted(
			(
				_working_sheet_capacity_signature(sheet)
				for sheet in state.working_sheets
			),
		)
	)


def _partial_state_selection_key(state: _SearchState) -> tuple[int, float]:
	return (state.placed_part_count, state.placed_area_mm2)


def _state_to_cutting_result(
	state: _SearchState,
	settings: CutSettings,
	remaining_part_units: tuple[optimizer._PartUnit, ...],
) -> CuttingResult:
	sheet_results = [
		optimizer._to_sheet_cut_result(working_sheet, settings)
		for working_sheet in state.working_sheets
		if working_sheet.placed_parts
	]
	unplaced_parts = [
		UnplacedPart(
			part_number=part_unit.unit_number,
			source_part_number=part_unit.part.number,
			part_name=part_unit.part.name,
			reason_code="SHEET_LIMIT_SEARCH_NOT_PLACED",
			reason="Деталь не размещена в пределах ограниченного поиска по числу листов.",
		)
		for part_unit in remaining_part_units
	]
	return assemble_cutting_result(
		sheets=sheet_results,
		unplaced_parts=unplaced_parts,
	)
