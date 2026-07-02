from dataclasses import dataclass, field
from enum import Enum

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cut_tree import CutDirection, CutLine, CutNode, RectArea
from cutting_app.app.domain.cutting_result import (
	CuttingResult,
	PlacedPart,
	SheetCutResult,
	UnplacedPart,
)
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.domain.sheet import SheetInput
from cutting_app.app.services.placement_calculator import calculate_placed_dimensions
from cutting_app.app.services.sheet_calculator import calculate_usable_sheet_area
from cutting_app.app.services.size_calculator import calculate_part_sizes


class SplitStrategy(str, Enum):
	VERTICAL_FIRST = "vertical_first"
	HORIZONTAL_FIRST = "horizontal_first"


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
) -> CuttingResult:
	working_sheets = _create_working_sheets(sheets)
	part_units = _expand_and_sort_parts(parts)
	unplaced_parts: list[UnplacedPart] = []

	for part_unit in part_units:
		placed = False

		for working_sheet in working_sheets:
			candidate = _find_best_candidate(working_sheet, part_unit.part, settings)
			if candidate is None:
				continue

			_place_candidate(
				working_sheet=working_sheet,
				part_unit=part_unit,
				candidate=candidate,
				settings=settings,
			)
			placed = True
			break

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

	return CuttingResult(
		sheets=[_to_sheet_cut_result(sheet) for sheet in working_sheets if sheet.placed_parts],
		unplaced_parts=unplaced_parts,
	)


def _create_working_sheets(sheets: list[SheetInput]) -> list[_WorkingSheet]:
	working_sheets: list[_WorkingSheet] = []

	for sheet in _sort_sheets(sheets):
		for copy_index in range(sheet.quantity):
			usable_area = calculate_usable_sheet_area(sheet)
			root = CutNode(
				area=RectArea(
					x_mm=usable_area.x_mm,
					y_mm=usable_area.y_mm,
					width_mm=usable_area.width_mm,
					height_mm=usable_area.height_mm,
				)
			)
			name = _make_sheet_copy_name(sheet, copy_index)
			working_sheets.append(
				_WorkingSheet(
					sheet=sheet,
					name=name,
					root=root,
					free_nodes=[_FreeNode(root)],
				)
			)

	return working_sheets


def _sort_sheets(sheets: list[SheetInput]) -> list[SheetInput]:
	return sorted(
		sheets,
		key=lambda sheet: (
			0 if sheet.is_remnant else 1,
			sheet.width_mm * sheet.height_mm,
			sheet.name,
		),
	)


def _make_sheet_copy_name(sheet: SheetInput, copy_index: int) -> str:
	if sheet.quantity == 1:
		return sheet.name
	return f"{sheet.name} #{copy_index + 1}"


def _expand_and_sort_parts(parts: list[PartInput]) -> list[_PartUnit]:
	part_units: list[_PartUnit] = []

	for part in parts:
		for copy_index in range(part.quantity):
			unit_number = part.number if part.quantity == 1 else f"{part.number}-{copy_index + 1}"
			part_units.append(_PartUnit(part=part, unit_number=unit_number))

	return sorted(
		part_units,
		key=lambda part_unit: _part_sort_key(part_unit.part, part_unit.unit_number),
	)


def _part_sort_key(part: PartInput, unit_number: str) -> tuple[float, float, float, str]:
	sizes = calculate_part_sizes(part)
	area = sizes.cutting_l_mm * sizes.cutting_w_mm
	long_side = max(sizes.cutting_l_mm, sizes.cutting_w_mm)
	short_side = min(sizes.cutting_l_mm, sizes.cutting_w_mm)
	return (-area, -long_side, -short_side, unit_number)


def _find_best_candidate(
	working_sheet: _WorkingSheet,
	part: PartInput,
	settings: CutSettings,
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
					),
				)
			)

	if not candidates:
		return None

	return min(
		candidates,
		key=lambda candidate: _score_placement_candidate(candidate, settings.kerf_width_mm),
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
) -> tuple[float, float, float, float, float, float, int, int]:
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
	rotation_order = 0 if candidate.rotation == Rotation.DEG_0 else 1
	split_order = 0 if candidate.split_strategy == SplitStrategy.VERTICAL_FIRST else 1

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
			working_sheet.free_nodes.append(_FreeNode(free_node.node.second))
			working_sheet.free_nodes.append(_FreeNode(free_node.node.first.second))
		else:
			_apply_horizontal_first_two_step_split(
				free_node=free_node,
				part_area=part_area,
				right_area=right_area,
				bottom_area=bottom_area,
				part_number=part_unit.unit_number,
				kerf_width_mm=settings.kerf_width_mm,
			)
			working_sheet.free_nodes.append(_FreeNode(free_node.node.second))
			working_sheet.free_nodes.append(_FreeNode(free_node.node.first.second))
	elif right_area is not None:
		_apply_single_vertical_split(
			free_node=free_node,
			part_area=part_area,
			right_area=right_area,
			part_number=part_unit.unit_number,
			kerf_width_mm=settings.kerf_width_mm,
		)
		working_sheet.free_nodes.append(_FreeNode(free_node.node.second))
	elif bottom_area is not None:
		_apply_single_horizontal_split(
			free_node=free_node,
			part_area=part_area,
			bottom_area=bottom_area,
			part_number=part_unit.unit_number,
			kerf_width_mm=settings.kerf_width_mm,
		)
		working_sheet.free_nodes.append(_FreeNode(free_node.node.second))
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
		)
	)


def _select_split_strategy(
	area: RectArea,
	part_width_mm: float,
	part_height_mm: float,
	kerf_width_mm: float,
) -> SplitStrategy:
	if _make_right_area(area, part_width_mm, part_height_mm, kerf_width_mm, SplitStrategy.VERTICAL_FIRST) is None:
		return SplitStrategy.HORIZONTAL_FIRST
	if _make_bottom_area(area, part_width_mm, part_height_mm, kerf_width_mm, SplitStrategy.HORIZONTAL_FIRST) is None:
		return SplitStrategy.VERTICAL_FIRST

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
	width_mm = area.width_mm - part_width_mm - kerf_width_mm
	if width_mm <= 0:
		return None

	height_mm = area.height_mm
	if strategy == SplitStrategy.HORIZONTAL_FIRST:
		height_mm = part_height_mm

	return RectArea(
		x_mm=area.x_mm + part_width_mm + kerf_width_mm,
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
	height_mm = area.height_mm - part_height_mm - kerf_width_mm
	if height_mm <= 0:
		return None

	width_mm = part_width_mm
	if strategy == SplitStrategy.HORIZONTAL_FIRST:
		width_mm = area.width_mm

	return RectArea(
		x_mm=area.x_mm,
		y_mm=area.y_mm + part_height_mm + kerf_width_mm,
		width_mm=width_mm,
		height_mm=height_mm,
	)


def _apply_vertical_first_two_step_split(
	free_node: _FreeNode,
	part_area: RectArea,
	right_area: RectArea,
	bottom_area: RectArea,
	part_number: str,
	kerf_width_mm: float,
) -> None:
	area = free_node.node.area
	left_strip = RectArea(
		x_mm=area.x_mm,
		y_mm=area.y_mm,
		width_mm=part_area.width_mm,
		height_mm=area.height_mm,
	)

	free_node.node.cut = CutLine(
		direction=CutDirection.VERTICAL,
		position_mm=area.x_mm + part_area.width_mm,
		kerf_width_mm=kerf_width_mm,
	)
	free_node.node.first = CutNode(area=left_strip)
	free_node.node.second = CutNode(area=right_area)

	free_node.node.first.cut = CutLine(
		direction=CutDirection.HORIZONTAL,
		position_mm=area.y_mm + part_area.height_mm,
		kerf_width_mm=kerf_width_mm,
	)
	free_node.node.first.first = CutNode(area=part_area, part_number=part_number)
	free_node.node.first.second = CutNode(area=bottom_area)


def _apply_horizontal_first_two_step_split(
	free_node: _FreeNode,
	part_area: RectArea,
	right_area: RectArea,
	bottom_area: RectArea,
	part_number: str,
	kerf_width_mm: float,
) -> None:
	area = free_node.node.area
	top_strip = RectArea(
		x_mm=area.x_mm,
		y_mm=area.y_mm,
		width_mm=area.width_mm,
		height_mm=part_area.height_mm,
	)

	free_node.node.cut = CutLine(
		direction=CutDirection.HORIZONTAL,
		position_mm=area.y_mm + part_area.height_mm,
		kerf_width_mm=kerf_width_mm,
	)
	free_node.node.first = CutNode(area=top_strip)
	free_node.node.second = CutNode(area=bottom_area)

	free_node.node.first.cut = CutLine(
		direction=CutDirection.VERTICAL,
		position_mm=area.x_mm + part_area.width_mm,
		kerf_width_mm=kerf_width_mm,
	)
	free_node.node.first.first = CutNode(area=part_area, part_number=part_number)
	free_node.node.first.second = CutNode(area=right_area)


def _apply_single_vertical_split(
	free_node: _FreeNode,
	part_area: RectArea,
	right_area: RectArea,
	part_number: str,
	kerf_width_mm: float,
) -> None:
	free_node.node.cut = CutLine(
		direction=CutDirection.VERTICAL,
		position_mm=part_area.x_mm + part_area.width_mm,
		kerf_width_mm=kerf_width_mm,
	)
	free_node.node.first = CutNode(area=part_area, part_number=part_number)
	free_node.node.second = CutNode(area=right_area)


def _apply_single_horizontal_split(
	free_node: _FreeNode,
	part_area: RectArea,
	bottom_area: RectArea,
	part_number: str,
	kerf_width_mm: float,
) -> None:
	free_node.node.cut = CutLine(
		direction=CutDirection.HORIZONTAL,
		position_mm=part_area.y_mm + part_area.height_mm,
		kerf_width_mm=kerf_width_mm,
	)
	free_node.node.first = CutNode(area=part_area, part_number=part_number)
	free_node.node.second = CutNode(area=bottom_area)


def _to_sheet_cut_result(working_sheet: _WorkingSheet) -> SheetCutResult:
	return SheetCutResult(
		sheet_name=working_sheet.name,
		sheet_width_mm=working_sheet.sheet.width_mm,
		sheet_height_mm=working_sheet.sheet.height_mm,
		root=working_sheet.root,
		placed_parts=working_sheet.placed_parts,
		waste_areas=[free_node.node.area for free_node in working_sheet.free_nodes],
	)
