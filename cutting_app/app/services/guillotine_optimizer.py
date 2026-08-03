from dataclasses import dataclass, field
from enum import Enum

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cut_tree import CutDirection, CutLine, CutNode, RectArea
from cutting_app.app.domain.cutting_result import (
	ActualCut,
	CuttingResult,
	PlacedPart,
	SheetCutMetrics,
	SheetCutResult,
	UnplacedPart,
)
from cutting_app.app.domain.edge_consumption import EdgeSegment
from cutting_app.app.domain.optimization import (
	OptimizationVariant,
	PartOrdering,
	PlacementHeuristic,
	RotationPreference,
	SheetSelectionHeuristic,
	SplitHeuristic,
)
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.domain.return_remnant import ReturnRemnantSettings
from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.services.area_metrics_calculator import (
	calculate_material_utilization_percent,
	calculate_working_area_efficiency_percent,
)
from cutting_app.app.services.edge_consumption_calculator import (
	build_part_edge_segments,
	summarize_edge_segments,
)
from cutting_app.app.services.cutting_variant_selector import (
	EvaluatedCuttingVariant,
	select_best_cutting_variant,
)
from cutting_app.app.services.cutting_result_assembler import (
	assemble_cutting_result,
)
from cutting_app.app.services.guillotine_optimization_variants import (
	build_default_optimization_variants,
	build_operation_refinement_variants,
)
from cutting_app.app.services.multi_window_variant_builder import (
	build_multi_window_combination_candidates,
)
from cutting_app.app.services.placement_calculator import calculate_placed_dimensions
from cutting_app.app.services.production_cut_plan_builder import build_production_cut_plan
from cutting_app.app.services.return_remnant_calculator import attach_return_remnants
from cutting_app.app.services.sheet_calculator import calculate_usable_sheet_area
from cutting_app.app.services.size_calculator import calculate_part_sizes


class SplitStrategy(str, Enum):
	VERTICAL_FIRST = "vertical_first"
	HORIZONTAL_FIRST = "horizontal_first"


_MAX_LOCAL_REBUILD_SUFFIX_SHEETS = 7
_MAX_OPERATION_REBUILD_WINDOW_SHEETS = 7


@dataclass(frozen=True)
class _PartUnit:
	part: PartInput
	unit_number: str


@dataclass
class _FreeNode:
	node: CutNode


@dataclass
class _WorkingSheet:
	sheet: SheetInput
	name: str
	root: CutNode
	free_nodes: list[_FreeNode] = field(default_factory=list)
	placed_parts: list[PlacedPart] = field(default_factory=list)
	waste_areas: list[RectArea] = field(default_factory=list)
	edge_segments: list[EdgeSegment] = field(default_factory=list)


@dataclass(frozen=True)
class _PlacementCandidate:
	free_node: _FreeNode
	rotation: Rotation
	width_mm: float
	height_mm: float
	split_strategy: SplitStrategy


@dataclass(frozen=True)
class _SplitAreas:
	right_area: RectArea | None
	bottom_area: RectArea | None


def optimize_guillotine_cutting(
	parts: list[PartInput],
	sheets: list[SheetInput],
	settings: CutSettings,
	return_remnant_settings: ReturnRemnantSettings | None = None,
) -> CuttingResult:
	effective_return_remnant_settings = (
		return_remnant_settings or ReturnRemnantSettings()
	)
	variants = build_default_optimization_variants()
	base_evaluated = [
		EvaluatedCuttingVariant(
			variant_id=variant.variant_id,
			technical_order=variant.technical_order,
			result=_optimize_guillotine_cutting_variant(
				parts=parts,
				sheets=sheets,
				settings=settings,
				variant=variant,
			),
		)
		for variant in variants
	]
	base_result = select_best_cutting_variant(
		base_evaluated,
		return_remnant_settings=effective_return_remnant_settings,
		prioritize_return_remnants=False,
	)
	local_evaluated = _build_local_rebuild_candidates(
		parts=parts,
		settings=settings,
		variants=variants,
		seed_result=base_result,
		technical_order_start=len(base_evaluated),
	)
	capacity_evaluated = [*base_evaluated, *local_evaluated]
	capacity_result = select_best_cutting_variant(
		capacity_evaluated,
		return_remnant_settings=effective_return_remnant_settings,
		prioritize_return_remnants=False,
	)
	operation_evaluated = _build_operation_refinement_candidates(
		parts=parts,
		settings=settings,
		variants=build_operation_refinement_variants(),
		seed_result=capacity_result,
		technical_order_start=len(capacity_evaluated),
	)
	multi_window_evaluated = build_multi_window_combination_candidates(
		seed_result=capacity_result,
		window_candidates=operation_evaluated,
		return_remnant_settings=effective_return_remnant_settings,
		technical_order_start=len(capacity_evaluated) + len(operation_evaluated),
	)

	selected_result = select_best_cutting_variant(
		[
			*capacity_evaluated,
			*operation_evaluated,
			*multi_window_evaluated,
		],
		return_remnant_settings=effective_return_remnant_settings,
	)
	return attach_return_remnants(
		selected_result,
		effective_return_remnant_settings,
	)


def _optimize_guillotine_cutting_variant(
	parts: list[PartInput],
	sheets: list[SheetInput],
	settings: CutSettings,
	variant: OptimizationVariant,
) -> CuttingResult:
	return _optimize_part_units_variant(
		part_units=_expand_parts(parts),
		working_sheets=_create_working_sheets(sheets),
		settings=settings,
		variant=variant,
	)


def _optimize_part_units_variant(
	part_units: list[_PartUnit],
	working_sheets: list[_WorkingSheet],
	settings: CutSettings,
	variant: OptimizationVariant,
) -> CuttingResult:
	part_units = _sort_part_units(part_units, variant.part_ordering)
	unplaced_parts: list[UnplacedPart] = []

	for part_unit in part_units:
		if variant.sheet_selection_heuristic == SheetSelectionHeuristic.FIRST_FIT:
			selected = _find_first_fit_sheet_candidate(
				working_sheets=working_sheets,
				part=part_unit.part,
				settings=settings,
				variant=variant,
			)
		else:
			selected = _find_best_sheet_candidate(
				working_sheets=working_sheets,
				part=part_unit.part,
				settings=settings,
				variant=variant,
			)
		placed = selected is not None

		if selected is not None:
			working_sheet, candidate = selected
			_place_candidate(
				working_sheet=working_sheet,
				part_unit=part_unit,
				candidate=candidate,
				settings=settings,
			)

		if not placed:
			unplaced_parts.append(
				UnplacedPart(
					part_number=part_unit.unit_number,
					source_part_number=part_unit.part.number,
					part_name=part_unit.part.name,
					reason_code="DETAIL_DOES_NOT_FIT",
					reason="Деталь не помещается ни на один доступный лист с учётом поворота, отступов и пропила.",
				)
			)

	sheet_results = [
		_to_sheet_cut_result(sheet, settings)
		for sheet in working_sheets
		if sheet.placed_parts
	]

	return assemble_cutting_result(
		sheets=sheet_results,
		unplaced_parts=unplaced_parts,
	)


def _find_first_fit_sheet_candidate(
	working_sheets: list[_WorkingSheet],
	part: PartInput,
	settings: CutSettings,
	variant: OptimizationVariant,
) -> tuple[_WorkingSheet, _PlacementCandidate] | None:
	for working_sheet in working_sheets:
		candidate = _find_best_candidate(
			working_sheet,
			part,
			settings,
			variant,
		)
		if candidate is not None:
			return working_sheet, candidate
	return None


def _find_best_sheet_candidate(
	working_sheets: list[_WorkingSheet],
	part: PartInput,
	settings: CutSettings,
	variant: OptimizationVariant,
) -> tuple[_WorkingSheet, _PlacementCandidate] | None:
	fit_candidates: list[tuple[int, _WorkingSheet, _PlacementCandidate]] = []

	for sheet_index, working_sheet in enumerate(working_sheets):
		candidate = _find_best_candidate(
			working_sheet,
			part,
			settings,
			variant,
		)
		if candidate is None:
			continue
		fit_candidates.append((sheet_index, working_sheet, candidate))

	if not fit_candidates:
		return None

	best_stock_key = min(
		_sheet_priority_key(working_sheet.sheet)
		for _, working_sheet, _ in fit_candidates
	)
	priority_candidates = [
		item
		for item in fit_candidates
		if _sheet_priority_key(item[1].sheet) == best_stock_key
	]
	used_candidates = [
		item
		for item in priority_candidates
		if item[1].placed_parts
	]

	if used_candidates:
		_, working_sheet, candidate = min(
			used_candidates,
			key=lambda item: (
				*_score_placement_candidate(
					item[2],
					settings.kerf_width_mm,
					variant.placement_heuristic,
					variant.rotation_preference,
				),
				item[0],
			),
		)
		return working_sheet, candidate

	_, working_sheet, candidate = min(
		priority_candidates,
		key=lambda item: item[0],
	)
	return working_sheet, candidate


def _build_local_rebuild_candidates(
	parts: list[PartInput],
	settings: CutSettings,
	variants: tuple[OptimizationVariant, ...],
	seed_result: CuttingResult,
	technical_order_start: int,
) -> list[EvaluatedCuttingVariant]:
	if seed_result.unplaced_parts or len(seed_result.sheets) < 3:
		return []

	part_units_by_number = _build_unique_part_unit_lookup(parts)
	if part_units_by_number is None:
		return []
	max_suffix_size = min(
		_MAX_LOCAL_REBUILD_SUFFIX_SHEETS,
		len(seed_result.sheets) - 1,
	)
	seed_variant_id = _selected_variant_id(seed_result)
	candidates: list[EvaluatedCuttingVariant] = []

	for suffix_size in range(2, max_suffix_size + 1):
		suffix_sheets = seed_result.sheets[-suffix_size:]
		part_units = [
			part_units_by_number[placed_part.part_number]
			for sheet in suffix_sheets
			for placed_part in sheet.placed_parts
		]
		rebuild_slots = suffix_sheets[:-1]

		for variant in variants:
			rebuilt_suffix = _optimize_part_units_variant(
				part_units=part_units,
				working_sheets=_create_rebuild_working_sheets(rebuild_slots),
				settings=settings,
				variant=variant,
			)
			candidate_result = _combine_rebuilt_suffix(
				seed_result=seed_result,
				suffix_size=suffix_size,
				rebuilt_suffix=rebuilt_suffix,
			)
			candidates.append(
				EvaluatedCuttingVariant(
					variant_id=_make_local_rebuild_variant_id(
						suffix_size=suffix_size,
						seed_variant_id=seed_variant_id,
						rebuild_variant_id=variant.variant_id,
					),
					technical_order=technical_order_start + len(candidates),
					result=candidate_result,
				)
			)

	return candidates


def _build_operation_refinement_candidates(
	parts: list[PartInput],
	settings: CutSettings,
	variants: tuple[OptimizationVariant, ...],
	seed_result: CuttingResult,
	technical_order_start: int,
) -> list[EvaluatedCuttingVariant]:
	if seed_result.unplaced_parts or len(seed_result.sheets) < 2:
		return []

	part_units_by_number = _build_unique_part_unit_lookup(parts)
	if part_units_by_number is None:
		return []
	max_window_size = min(
		_MAX_OPERATION_REBUILD_WINDOW_SHEETS,
		len(seed_result.sheets),
	)
	seed_variant_id = _selected_variant_id(seed_result)
	candidates: list[EvaluatedCuttingVariant] = []

	for window_size in range(2, max_window_size + 1):
		for window_start in range(len(seed_result.sheets) - window_size + 1):
			window_sheets = seed_result.sheets[
				window_start:window_start + window_size
			]
			part_units = [
				part_units_by_number[placed_part.part_number]
				for sheet in window_sheets
				for placed_part in sheet.placed_parts
			]

			for variant in variants:
				rebuilt_window = _optimize_part_units_variant(
					part_units=part_units,
					working_sheets=_create_rebuild_working_sheets(window_sheets),
					settings=settings,
					variant=variant,
				)
				candidate_result = _combine_rebuilt_window(
					seed_result=seed_result,
					window_start=window_start,
					window_size=window_size,
					rebuilt_window=rebuilt_window,
				)
				candidates.append(
					EvaluatedCuttingVariant(
						variant_id=_make_operation_refinement_variant_id(
							window_start=window_start,
							window_size=window_size,
							seed_variant_id=seed_variant_id,
							rebuild_variant_id=variant.variant_id,
						),
						technical_order=technical_order_start + len(candidates),
						result=candidate_result,
						rebuilt_window_start=window_start,
						rebuilt_window_size=window_size,
					)
				)

	return candidates


def _build_unique_part_unit_lookup(
	parts: list[PartInput],
) -> dict[str, _PartUnit] | None:
	part_units_by_number: dict[str, _PartUnit] = {}
	for part_unit in _expand_parts(parts):
		if part_unit.unit_number in part_units_by_number:
			return None
		part_units_by_number[part_unit.unit_number] = part_unit
	return part_units_by_number


def _selected_variant_id(result: CuttingResult) -> str:
	if result.optimization is None:
		raise ValueError("Для локальной перестройки отсутствуют сведения о базовом варианте.")
	return result.optimization.selected_variant_id


def _create_rebuild_working_sheets(
	sheet_slots: list[SheetCutResult],
) -> list[_WorkingSheet]:
	return [
		_create_working_sheet(
			sheet=_sheet_input_from_result(sheet_result),
			name=sheet_result.sheet_name,
		)
		for sheet_result in sheet_slots
	]


def _sheet_input_from_result(sheet_result: SheetCutResult) -> SheetInput:
	usable_area = sheet_result.root.area
	return SheetInput(
		name=sheet_result.sheet_stock_name or sheet_result.sheet_name,
		width_mm=sheet_result.sheet_width_mm,
		height_mm=sheet_result.sheet_height_mm,
		is_remnant=sheet_result.sheet_is_remnant,
		margins=SheetMargins(
			left_mm=usable_area.x_mm,
			top_mm=usable_area.y_mm,
			right_mm=sheet_result.sheet_width_mm - usable_area.right_mm,
			bottom_mm=sheet_result.sheet_height_mm - usable_area.bottom_mm,
		),
	)


def _combine_rebuilt_suffix(
	seed_result: CuttingResult,
	suffix_size: int,
	rebuilt_suffix: CuttingResult,
) -> CuttingResult:
	return _combine_rebuilt_window(
		seed_result=seed_result,
		window_start=len(seed_result.sheets) - suffix_size,
		window_size=suffix_size,
		rebuilt_window=rebuilt_suffix,
	)


def _combine_rebuilt_window(
	seed_result: CuttingResult,
	window_start: int,
	window_size: int,
	rebuilt_window: CuttingResult,
) -> CuttingResult:
	sheets = [
		*seed_result.sheets[:window_start],
		*rebuilt_window.sheets,
		*seed_result.sheets[window_start + window_size:],
	]
	unplaced_parts = rebuilt_window.unplaced_parts

	return assemble_cutting_result(
		sheets=sheets,
		unplaced_parts=unplaced_parts,
	)


def _make_local_rebuild_variant_id(
	suffix_size: int,
	seed_variant_id: str,
	rebuild_variant_id: str,
) -> str:
	return (
		f"local_suffix_{suffix_size}_to_{suffix_size - 1}"
		f"__seed_{seed_variant_id}"
		f"__rebuild_{rebuild_variant_id}"
	)


def _make_operation_refinement_variant_id(
	window_start: int,
	window_size: int,
	seed_variant_id: str,
	rebuild_variant_id: str,
) -> str:
	window_number = window_start + 1
	window_end = window_start + window_size
	return (
		f"operation_window_{window_number}_to_{window_end}"
		f"__seed_{seed_variant_id}"
		f"__rebuild_{rebuild_variant_id}"
	)


def _create_working_sheets(sheets: list[SheetInput]) -> list[_WorkingSheet]:
	working_sheets: list[_WorkingSheet] = []

	for sheet in _sort_sheets(sheets):
		for copy_index in range(sheet.quantity):
			working_sheets.append(
				_create_working_sheet(
					sheet=sheet,
					name=_make_sheet_copy_name(sheet, copy_index),
				)
			)

	return working_sheets


def _create_working_sheet(sheet: SheetInput, name: str) -> _WorkingSheet:
	usable_area = calculate_usable_sheet_area(sheet)
	root = CutNode(
		area=RectArea(
			x_mm=usable_area.x_mm,
			y_mm=usable_area.y_mm,
			width_mm=usable_area.width_mm,
			height_mm=usable_area.height_mm,
		),
		is_waste=True,
	)
	return _WorkingSheet(
		sheet=sheet,
		name=name,
		root=root,
		free_nodes=[_FreeNode(root)],
	)


def _sort_sheets(sheets: list[SheetInput]) -> list[SheetInput]:
	return sorted(sheets, key=_sheet_sort_key)


def _sheet_sort_key(sheet: SheetInput) -> tuple[int, float, str]:
	return _sheet_priority_key(sheet)


def _sheet_priority_key(sheet: SheetInput) -> tuple[int, float, str]:
	return (
		0 if sheet.is_remnant else 1,
		sheet.width_mm * sheet.height_mm,
		sheet.name,
	)


def _make_sheet_copy_name(sheet: SheetInput, copy_index: int) -> str:
	if sheet.quantity == 1:
		return sheet.name
	return f"{sheet.name} #{copy_index + 1}"


def _expand_and_sort_parts(
	parts: list[PartInput],
	part_ordering: PartOrdering,
) -> list[_PartUnit]:
	return _sort_part_units(_expand_parts(parts), part_ordering)


def _expand_parts(parts: list[PartInput]) -> list[_PartUnit]:
	part_units: list[_PartUnit] = []

	for part in parts:
		for copy_index in range(part.quantity):
			unit_number = part.number if part.quantity == 1 else f"{part.number}-{copy_index + 1}"
			part_units.append(_PartUnit(part=part, unit_number=unit_number))

	return part_units


def _sort_part_units(
	part_units: list[_PartUnit],
	part_ordering: PartOrdering,
) -> list[_PartUnit]:
	return sorted(
		part_units,
		key=lambda part_unit: _part_sort_key(
			part_unit.part,
			part_unit.unit_number,
			part_ordering,
		),
	)


def _part_sort_key(
	part: PartInput,
	unit_number: str,
	part_ordering: PartOrdering,
) -> tuple[float, float, float, str]:
	sizes = calculate_part_sizes(part)
	area = sizes.cutting_l_mm * sizes.cutting_w_mm
	long_side = max(sizes.cutting_l_mm, sizes.cutting_w_mm)
	short_side = min(sizes.cutting_l_mm, sizes.cutting_w_mm)

	if part_ordering == PartOrdering.LONG_SIDE_DESC:
		return (-long_side, -area, -short_side, unit_number)

	if part_ordering == PartOrdering.SHORT_SIDE_DESC:
		return (-short_side, -area, -long_side, unit_number)

	return (-area, -long_side, -short_side, unit_number)


def _find_best_candidate(
	working_sheet: _WorkingSheet,
	part: PartInput,
	settings: CutSettings,
	variant: OptimizationVariant,
) -> _PlacementCandidate | None:
	part_sizes = calculate_part_sizes(part)
	candidates: list[_PlacementCandidate] = []

	for free_node in _sorted_free_nodes(working_sheet.free_nodes):
		for rotation in _allowed_rotations(part):
			dimensions = calculate_placed_dimensions(part_sizes, rotation)
			if not _fits(free_node.node.area, dimensions.width_mm, dimensions.height_mm):
				continue

			candidates.append(
				_PlacementCandidate(
					free_node=free_node,
					rotation=rotation,
					width_mm=dimensions.width_mm,
					height_mm=dimensions.height_mm,
					split_strategy=_select_split_strategy(
						area=free_node.node.area,
						part_width_mm=dimensions.width_mm,
						part_height_mm=dimensions.height_mm,
						kerf_width_mm=settings.kerf_width_mm,
						split_heuristic=variant.split_heuristic,
					),
				)
			)

	if not candidates:
		return None

	return min(
		candidates,
		key=lambda candidate: _score_placement_candidate(
			candidate,
			settings.kerf_width_mm,
			variant.placement_heuristic,
			variant.rotation_preference,
		),
	)


def _sorted_free_nodes(free_nodes: list[_FreeNode]) -> list[_FreeNode]:
	return sorted(
		free_nodes,
		key=lambda free_node: (
			free_node.node.area.y_mm,
			free_node.node.area.x_mm,
			free_node.node.area.width_mm * free_node.node.area.height_mm,
		),
	)


def _allowed_rotations(part: PartInput) -> list[Rotation]:
	if part.rotation_allowed:
		return [Rotation.DEG_0, Rotation.DEG_90]
	return [Rotation.DEG_0]


def _fits(area: RectArea, width_mm: float, height_mm: float) -> bool:
	return width_mm <= area.width_mm and height_mm <= area.height_mm


def _score_placement_candidate(
	candidate: _PlacementCandidate,
	kerf_width_mm: float,
	placement_heuristic: PlacementHeuristic,
	rotation_preference: RotationPreference,
) -> tuple[float, ...]:
	area = candidate.free_node.node.area
	area_excess = area.width_mm * area.height_mm - candidate.width_mm * candidate.height_mm
	width_gap = area.width_mm - candidate.width_mm
	height_gap = area.height_mm - candidate.height_mm
	short_gap = min(width_gap, height_gap)
	long_gap = max(width_gap, height_gap)
	kerf_loss_area = _score_split_strategy(
		area=area,
		part_width_mm=candidate.width_mm,
		part_height_mm=candidate.height_mm,
		kerf_width_mm=kerf_width_mm,
		strategy=candidate.split_strategy,
	)[0]
	preferred_rotation = (
		Rotation.DEG_0
		if rotation_preference == RotationPreference.UNROTATED_FIRST
		else Rotation.DEG_90
	)
	rotation_order = 0 if candidate.rotation == preferred_rotation else 1
	split_order = 0 if candidate.split_strategy == SplitStrategy.VERTICAL_FIRST else 1

	if placement_heuristic == PlacementHeuristic.BEST_SHORT_SIDE_FIT:
		return (
			short_gap,
			long_gap,
			area_excess,
			kerf_loss_area,
			rotation_order,
			area.y_mm,
			area.x_mm,
			split_order,
		)

	return (
		area_excess,
		rotation_order,
		kerf_loss_area,
		short_gap,
		long_gap,
		area.y_mm,
		area.x_mm,
		split_order,
	)


def _place_candidate(
	working_sheet: _WorkingSheet,
	part_unit: _PartUnit,
	candidate: _PlacementCandidate,
	settings: CutSettings,
) -> None:
	free_node = candidate.free_node
	area = free_node.node.area
	working_sheet.free_nodes.remove(free_node)
	free_node.node.is_waste = False

	part_area = RectArea(
		x_mm=area.x_mm,
		y_mm=area.y_mm,
		width_mm=candidate.width_mm,
		height_mm=candidate.height_mm,
	)

	split_areas = _make_split_areas(
		area=area,
		part_width_mm=candidate.width_mm,
		part_height_mm=candidate.height_mm,
		kerf_width_mm=settings.kerf_width_mm,
		strategy=candidate.split_strategy,
	)
	right_area = split_areas.right_area
	bottom_area = split_areas.bottom_area

	if right_area is not None and bottom_area is not None:
		if candidate.split_strategy == SplitStrategy.VERTICAL_FIRST:
			_apply_vertical_first_two_step_split(
				free_node=free_node,
				part_area=part_area,
				right_area=right_area,
				bottom_area=bottom_area,
				part_number=part_unit.unit_number,
				kerf_width_mm=settings.kerf_width_mm,
			)
			_append_free_node_if_positive(working_sheet, free_node.node.second)
			_append_free_node_if_positive(working_sheet, free_node.node.first.second)
		else:
			_apply_horizontal_first_two_step_split(
				free_node=free_node,
				part_area=part_area,
				right_area=right_area,
				bottom_area=bottom_area,
				part_number=part_unit.unit_number,
				kerf_width_mm=settings.kerf_width_mm,
			)
			_append_free_node_if_positive(working_sheet, free_node.node.second)
			_append_free_node_if_positive(working_sheet, free_node.node.first.second)
	elif right_area is not None:
		_apply_single_vertical_split(
			free_node=free_node,
			part_area=part_area,
			right_area=right_area,
			part_number=part_unit.unit_number,
			kerf_width_mm=settings.kerf_width_mm,
		)
		_append_free_node_if_positive(working_sheet, free_node.node.second)
	elif bottom_area is not None:
		_apply_single_horizontal_split(
			free_node=free_node,
			part_area=part_area,
			bottom_area=bottom_area,
			part_number=part_unit.unit_number,
			kerf_width_mm=settings.kerf_width_mm,
		)
		_append_free_node_if_positive(working_sheet, free_node.node.second)
	else:
		free_node.node.part_number = part_unit.unit_number

	working_sheet.placed_parts.append(
		PlacedPart(
			part_number=part_unit.unit_number,
			source_part_number=part_unit.part.number,
			part_name=part_unit.part.name,
			sheet_name=working_sheet.name,
			x_mm=part_area.x_mm,
			y_mm=part_area.y_mm,
			width_mm=part_area.width_mm,
			height_mm=part_area.height_mm,
			rotation=candidate.rotation,
			edges=part_unit.part.edges,
		)
	)
	working_sheet.edge_segments.extend(
		build_part_edge_segments(
			part=part_unit.part,
			part_number=part_unit.unit_number,
		)
	)

def _append_free_node_if_positive(
	working_sheet: _WorkingSheet,
	node: CutNode,
) -> None:
	if node.area.width_mm <= 0 or node.area.height_mm <= 0:
		return

	working_sheet.free_nodes.append(_FreeNode(node))



def _select_split_strategy(
	area: RectArea,
	part_width_mm: float,
	part_height_mm: float,
	kerf_width_mm: float,
	split_heuristic: SplitHeuristic,
) -> SplitStrategy:
	if _make_right_area(area, part_width_mm, part_height_mm, kerf_width_mm, SplitStrategy.VERTICAL_FIRST) is None:
		return SplitStrategy.HORIZONTAL_FIRST
	if _make_bottom_area(area, part_width_mm, part_height_mm, kerf_width_mm, SplitStrategy.HORIZONTAL_FIRST) is None:
		return SplitStrategy.VERTICAL_FIRST

	if split_heuristic == SplitHeuristic.SHORTER_LEFTOVER_AXIS:
		width_gap_mm = area.width_mm - part_width_mm
		height_gap_mm = area.height_mm - part_height_mm
		if width_gap_mm <= height_gap_mm:
			return SplitStrategy.VERTICAL_FIRST
		return SplitStrategy.HORIZONTAL_FIRST

	return min(
		[SplitStrategy.VERTICAL_FIRST, SplitStrategy.HORIZONTAL_FIRST],
		key=lambda strategy: _score_split_strategy(
			area=area,
			part_width_mm=part_width_mm,
			part_height_mm=part_height_mm,
			kerf_width_mm=kerf_width_mm,
			strategy=strategy,
		),
	)


def _score_split_strategy(
	area: RectArea,
	part_width_mm: float,
	part_height_mm: float,
	kerf_width_mm: float,
	strategy: SplitStrategy,
) -> tuple[float, float, float, int]:
	split_areas = _make_split_areas(
		area=area,
		part_width_mm=part_width_mm,
		part_height_mm=part_height_mm,
		kerf_width_mm=kerf_width_mm,
		strategy=strategy,
	)
	free_areas = [area for area in [split_areas.right_area, split_areas.bottom_area] if area is not None]
	free_area_sum = sum(free_area.width_mm * free_area.height_mm for free_area in free_areas)
	part_area = part_width_mm * part_height_mm
	kerf_loss_area = area.width_mm * area.height_mm - part_area - free_area_sum
	largest_free_area = max((free_area.width_mm * free_area.height_mm for free_area in free_areas), default=0)
	largest_short_side = max((min(free_area.width_mm, free_area.height_mm) for free_area in free_areas), default=0)
	tie_order = 0 if strategy == SplitStrategy.VERTICAL_FIRST else 1

	return (kerf_loss_area, -largest_free_area, -largest_short_side, tie_order)


def _make_split_areas(
	area: RectArea,
	part_width_mm: float,
	part_height_mm: float,
	kerf_width_mm: float,
	strategy: SplitStrategy,
) -> _SplitAreas:
	return _SplitAreas(
		right_area=_make_right_area(area, part_width_mm, part_height_mm, kerf_width_mm, strategy),
		bottom_area=_make_bottom_area(area, part_width_mm, part_height_mm, kerf_width_mm, strategy),
	)


def _make_right_area(
    area: RectArea,
    part_width_mm: float,
    part_height_mm: float,
    kerf_width_mm: float,
    strategy: SplitStrategy,
) -> RectArea | None:
    gap_width_mm = area.width_mm - part_width_mm

    if gap_width_mm <= 0:
        return None

    effective_kerf_width_mm = min(kerf_width_mm, gap_width_mm)
    width_mm = gap_width_mm - effective_kerf_width_mm

    height_mm = area.height_mm
    if strategy == SplitStrategy.HORIZONTAL_FIRST:
        height_mm = part_height_mm

    return RectArea(
        x_mm=area.x_mm + part_width_mm + effective_kerf_width_mm,
        y_mm=area.y_mm,
        width_mm=width_mm,
        height_mm=height_mm,
    )


def _make_bottom_area(
    area: RectArea,
    part_width_mm: float,
    part_height_mm: float,
    kerf_width_mm: float,
    strategy: SplitStrategy,
) -> RectArea | None:
    gap_height_mm = area.height_mm - part_height_mm

    if gap_height_mm <= 0:
        return None

    effective_kerf_width_mm = min(kerf_width_mm, gap_height_mm)
    height_mm = gap_height_mm - effective_kerf_width_mm

    width_mm = part_width_mm
    if strategy == SplitStrategy.HORIZONTAL_FIRST:
        width_mm = area.width_mm

    return RectArea(
        x_mm=area.x_mm,
        y_mm=area.y_mm + part_height_mm + effective_kerf_width_mm,
        width_mm=width_mm,
        height_mm=height_mm,
    )


def _effective_vertical_kerf_width(area: RectArea, part_area: RectArea, kerf_width_mm: float) -> float:
    gap_width_mm = area.right_mm - part_area.right_mm
    return min(kerf_width_mm, max(0, gap_width_mm))


def _effective_horizontal_kerf_width(area: RectArea, part_area: RectArea, kerf_width_mm: float) -> float:
    gap_height_mm = area.bottom_mm - part_area.bottom_mm
    return min(kerf_width_mm, max(0, gap_height_mm))

def _apply_vertical_first_two_step_split(
    free_node: _FreeNode,
    part_area: RectArea,
    right_area: RectArea,
    bottom_area: RectArea,
    part_number: str,
    kerf_width_mm: float,
) -> None:
    area = free_node.node.area
    vertical_kerf_width_mm = _effective_vertical_kerf_width(area, part_area, kerf_width_mm)
    horizontal_kerf_width_mm = _effective_horizontal_kerf_width(area, part_area, kerf_width_mm)

    left_strip = RectArea(
        x_mm=area.x_mm,
        y_mm=area.y_mm,
        width_mm=part_area.width_mm,
        height_mm=area.height_mm,
    )

    free_node.node.cut = CutLine(
        direction=CutDirection.VERTICAL,
        position_mm=area.x_mm + part_area.width_mm,
        kerf_width_mm=vertical_kerf_width_mm,
    )
    free_node.node.first = CutNode(area=left_strip)
    free_node.node.second = CutNode(area=right_area, is_waste=True)

    free_node.node.first.cut = CutLine(
        direction=CutDirection.HORIZONTAL,
        position_mm=area.y_mm + part_area.height_mm,
        kerf_width_mm=horizontal_kerf_width_mm,
    )
    free_node.node.first.first = CutNode(area=part_area, part_number=part_number)
    free_node.node.first.second = CutNode(area=bottom_area, is_waste=True)


def _apply_horizontal_first_two_step_split(
    free_node: _FreeNode,
    part_area: RectArea,
    right_area: RectArea,
    bottom_area: RectArea,
    part_number: str,
    kerf_width_mm: float,
) -> None:
    area = free_node.node.area
    horizontal_kerf_width_mm = _effective_horizontal_kerf_width(area, part_area, kerf_width_mm)
    vertical_kerf_width_mm = _effective_vertical_kerf_width(area, part_area, kerf_width_mm)

    top_strip = RectArea(
        x_mm=area.x_mm,
        y_mm=area.y_mm,
        width_mm=area.width_mm,
        height_mm=part_area.height_mm,
    )

    free_node.node.cut = CutLine(
        direction=CutDirection.HORIZONTAL,
        position_mm=area.y_mm + part_area.height_mm,
        kerf_width_mm=horizontal_kerf_width_mm,
    )
    free_node.node.first = CutNode(area=top_strip)
    free_node.node.second = CutNode(area=bottom_area, is_waste=True)

    free_node.node.first.cut = CutLine(
        direction=CutDirection.VERTICAL,
        position_mm=area.x_mm + part_area.width_mm,
        kerf_width_mm=vertical_kerf_width_mm,
    )
    free_node.node.first.first = CutNode(area=part_area, part_number=part_number)
    free_node.node.first.second = CutNode(area=right_area, is_waste=True)


def _apply_single_vertical_split(
    free_node: _FreeNode,
    part_area: RectArea,
    right_area: RectArea,
    part_number: str,
    kerf_width_mm: float,
) -> None:
    area = free_node.node.area
    vertical_kerf_width_mm = _effective_vertical_kerf_width(area, part_area, kerf_width_mm)

    free_node.node.cut = CutLine(
        direction=CutDirection.VERTICAL,
        position_mm=part_area.x_mm + part_area.width_mm,
        kerf_width_mm=vertical_kerf_width_mm,
    )
    free_node.node.first = CutNode(area=part_area, part_number=part_number)
    free_node.node.second = CutNode(area=right_area, is_waste=True)


def _apply_single_horizontal_split(
    free_node: _FreeNode,
    part_area: RectArea,
    bottom_area: RectArea,
    part_number: str,
    kerf_width_mm: float,
) -> None:
    area = free_node.node.area
    horizontal_kerf_width_mm = _effective_horizontal_kerf_width(area, part_area, kerf_width_mm)

    free_node.node.cut = CutLine(
        direction=CutDirection.HORIZONTAL,
        position_mm=part_area.y_mm + part_area.height_mm,
        kerf_width_mm=horizontal_kerf_width_mm,
    )
    free_node.node.first = CutNode(area=part_area, part_number=part_number)
    free_node.node.second = CutNode(area=bottom_area, is_waste=True)

def _to_sheet_cut_result(
	working_sheet: _WorkingSheet,
	settings: CutSettings,
) -> SheetCutResult:
	waste_areas = [free_node.node.area for free_node in working_sheet.free_nodes]
	actual_cuts = _collect_actual_cuts(working_sheet.root)
	production_cut_plan = build_production_cut_plan(
		plan_id=working_sheet.name,
		sheet_area=RectArea(
			x_mm=0,
			y_mm=0,
			width_mm=working_sheet.sheet.width_mm,
			height_mm=working_sheet.sheet.height_mm,
		),
		root=working_sheet.root,
		nominal_kerf_width_mm=settings.kerf_width_mm,
		initial_direction=settings.initial_cut_direction,
	)

	return SheetCutResult(
		sheet_name=working_sheet.name,
		sheet_width_mm=working_sheet.sheet.width_mm,
		sheet_height_mm=working_sheet.sheet.height_mm,
		root=working_sheet.root,
		sheet_stock_name=working_sheet.sheet.name,
		sheet_is_remnant=working_sheet.sheet.is_remnant,
		placed_parts=working_sheet.placed_parts,
		waste_areas=waste_areas,
		actual_cuts=actual_cuts,
		production_cut_plan=production_cut_plan,
		edge_consumption=summarize_edge_segments(working_sheet.edge_segments),
		metrics=_calculate_sheet_metrics(
			sheet_width_mm=working_sheet.sheet.width_mm,
			sheet_height_mm=working_sheet.sheet.height_mm,
			usable_area=working_sheet.root.area,
			placed_parts=working_sheet.placed_parts,
			waste_areas=waste_areas,
			actual_cuts=actual_cuts,
		),
	)


def _collect_actual_cuts(node: CutNode) -> list[ActualCut]:
	cuts: list[ActualCut] = []
	_collect_actual_cuts_into(node, cuts)
	return cuts


def _collect_actual_cuts_into(node: CutNode, cuts: list[ActualCut]) -> None:
	if node.cut is not None:
		cuts.append(_make_actual_cut(node))

	if node.first is not None:
		_collect_actual_cuts_into(node.first, cuts)

	if node.second is not None:
		_collect_actual_cuts_into(node.second, cuts)


def _make_actual_cut(node: CutNode) -> ActualCut:
	area = node.area
	cut = node.cut
	if cut is None:
		raise ValueError("Нельзя построить фактический рез для узла без линии реза.")

	if cut.direction == CutDirection.VERTICAL:
		return ActualCut(
			direction=cut.direction,
			x1_mm=cut.position_mm,
			y1_mm=area.y_mm,
			x2_mm=cut.position_mm,
			y2_mm=area.bottom_mm,
			kerf_width_mm=cut.kerf_width_mm,
		)

	return ActualCut(
		direction=cut.direction,
		x1_mm=area.x_mm,
		y1_mm=cut.position_mm,
		x2_mm=area.right_mm,
		y2_mm=cut.position_mm,
		kerf_width_mm=cut.kerf_width_mm,
	)


def _calculate_sheet_metrics(
	sheet_width_mm: float,
	sheet_height_mm: float,
	usable_area: RectArea,
	placed_parts: list[PlacedPart],
	waste_areas: list[RectArea],
	actual_cuts: list[ActualCut],
) -> SheetCutMetrics:
	sheet_area_mm2 = sheet_width_mm * sheet_height_mm
	usable_area_mm2 = usable_area.width_mm * usable_area.height_mm
	placed_area_mm2 = sum(part.width_mm * part.height_mm for part in placed_parts)
	waste_area_mm2 = sum(area.width_mm * area.height_mm for area in waste_areas)
	kerf_area_mm2 = sum(_actual_cut_length(cut) * cut.kerf_width_mm for cut in actual_cuts)

	return SheetCutMetrics(
		sheet_area_mm2=sheet_area_mm2,
		usable_area_mm2=usable_area_mm2,
		placed_area_mm2=placed_area_mm2,
		waste_area_mm2=waste_area_mm2,
		kerf_area_mm2=kerf_area_mm2,
		material_utilization_percent=calculate_material_utilization_percent(
			placed_area_mm2=placed_area_mm2,
			used_material_area_mm2=sheet_area_mm2,
		),
		working_area_efficiency_percent=calculate_working_area_efficiency_percent(
			placed_area_mm2=placed_area_mm2,
			working_area_mm2=usable_area_mm2,
		),
	)


def _actual_cut_length(cut: ActualCut) -> float:
	if cut.direction == CutDirection.VERTICAL:
		return cut.y2_mm - cut.y1_mm

	return cut.x2_mm - cut.x1_mm
