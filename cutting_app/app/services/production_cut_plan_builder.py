from dataclasses import dataclass

from cutting_app.app.domain.cut_tree import CutDirection, CutNode, RectArea
from cutting_app.app.domain.production_cut_plan import (
	CuttingCycle,
	CuttingCycleOutput,
	ProductionCutPlan,
	ProductionCutPlanMetrics,
	SizeSettingEvent,
	StripTurnEvent,
)
from cutting_app.app.services.cutting_cycle_builder import build_parallel_cutting_cycle
from cutting_app.app.services.size_setting_event_builder import (
	build_size_setting_events,
)
from cutting_app.app.services.strip_turn_event_builder import (
	build_strip_turn_events,
)


@dataclass(frozen=True)
class _TreeOutput:
	node: CutNode
	path: str


@dataclass
class _PlanBuildState:
	plan_id: str
	nominal_kerf_width_mm: float
	tolerance_mm: float
	cycles: list[CuttingCycle]

	def next_cycle_id(self) -> str:
		return f"{self.plan_id}:cycle:{len(self.cycles) + 1}"


def build_production_cut_plan(
	*,
	plan_id: str,
	sheet_area: RectArea,
	root: CutNode,
	nominal_kerf_width_mm: float,
	initial_direction: CutDirection = CutDirection.VERTICAL,
	tolerance_mm: float = 0.001,
) -> ProductionCutPlan:
	_validate_plan_input(
		plan_id=plan_id,
		sheet_area=sheet_area,
		root=root,
		nominal_kerf_width_mm=nominal_kerf_width_mm,
		tolerance_mm=tolerance_mm,
	)

	state = _PlanBuildState(
		plan_id=plan_id,
		nominal_kerf_width_mm=nominal_kerf_width_mm,
		tolerance_mm=tolerance_mm,
		cycles=[],
	)
	_build_node_cycles(
		node=root,
		node_path="root",
		source_area=sheet_area,
		state=state,
		parent_cycle_id=None,
		source_output_id=None,
		initial_direction=initial_direction,
	)
	cycles = tuple(state.cycles)
	strip_turns = build_strip_turn_events(
		plan_id=plan_id,
		cycles=cycles,
		tolerance_mm=tolerance_mm,
	)
	size_settings = build_size_setting_events(
		plan_id=plan_id,
		cycles=cycles,
		tolerance_mm=tolerance_mm,
	)

	return ProductionCutPlan(
		plan_id=plan_id,
		source_area=sheet_area,
		cycles=cycles,
		strip_turns=strip_turns,
		size_settings=size_settings,
		metrics=_calculate_plan_metrics(
			cycles=cycles,
			strip_turns=strip_turns,
			size_settings=size_settings,
		),
	)


def _validate_plan_input(
	*,
	plan_id: str,
	sheet_area: RectArea,
	root: CutNode,
	nominal_kerf_width_mm: float,
	tolerance_mm: float,
) -> None:
	if not plan_id.strip():
		raise ValueError("Идентификатор производственного плана не должен быть пустым.")

	if sheet_area.width_mm <= 0 or sheet_area.height_mm <= 0:
		raise ValueError("Физический лист должен иметь положительные размеры.")

	if nominal_kerf_width_mm <= 0:
		raise ValueError("Номинальная ширина пропила должна быть положительной.")

	if tolerance_mm < 0:
		raise ValueError("Допуск сравнения не может быть отрицательным.")

	if not _contains_area(sheet_area, root.area, tolerance_mm):
		raise ValueError("Рабочая область дерева резов выходит за физический лист.")


def _build_node_cycles(
	*,
	node: CutNode,
	node_path: str,
	source_area: RectArea,
	state: _PlanBuildState,
	parent_cycle_id: str | None,
	source_output_id: str | None,
	initial_direction: CutDirection,
) -> None:
	if not _contains_part(node):
		return

	direction = _select_cycle_direction(
		node=node,
		source_area=source_area,
		initial_direction=initial_direction,
		tolerance_mm=state.tolerance_mm,
	)
	if direction is None:
		return

	tree_outputs = _collect_cycle_outputs(node, node_path, direction)
	tree_outputs = _trim_terminal_waste_outputs(tree_outputs)
	if not tree_outputs:
		return

	cycle_id = state.next_cycle_id()
	outputs: list[CuttingCycleOutput] = []
	output_sources: list[tuple[_TreeOutput, CuttingCycleOutput]] = []

	for output_index, tree_output in enumerate(tree_outputs, start=1):
		output = CuttingCycleOutput(
			output_id=f"{cycle_id}:output:{output_index}",
			area=_project_output_area(
				output_area=tree_output.node.area,
				source_area=source_area,
				direction=direction,
			),
			part_number=tree_output.node.part_number,
			is_waste=not _contains_part(tree_output.node),
		)
		outputs.append(output)
		output_sources.append((tree_output, output))

	cycle = build_parallel_cutting_cycle(
		cycle_id=cycle_id,
		source_area=source_area,
		direction=direction,
		outputs=outputs,
		nominal_kerf_width_mm=state.nominal_kerf_width_mm,
		tolerance_mm=state.tolerance_mm,
		parent_cycle_id=parent_cycle_id,
		source_output_id=source_output_id,
	)
	state.cycles.append(cycle)

	for tree_output, output in output_sources:
		if not _contains_part(tree_output.node):
			continue

		_build_node_cycles(
			node=tree_output.node,
			node_path=tree_output.path,
			source_area=output.area,
			state=state,
			parent_cycle_id=cycle.cycle_id,
			source_output_id=output.output_id,
			initial_direction=_opposite_direction(direction),
		)


def _select_cycle_direction(
	*,
	node: CutNode,
	source_area: RectArea,
	initial_direction: CutDirection,
	tolerance_mm: float,
) -> CutDirection | None:
	if node.cut is not None:
		return node.cut.direction

	needs_vertical_trim = (
		abs(node.area.x_mm - source_area.x_mm) > tolerance_mm
		or abs(node.area.right_mm - source_area.right_mm) > tolerance_mm
	)
	needs_horizontal_trim = (
		abs(node.area.y_mm - source_area.y_mm) > tolerance_mm
		or abs(node.area.bottom_mm - source_area.bottom_mm) > tolerance_mm
	)

	if needs_vertical_trim and needs_horizontal_trim:
		return initial_direction
	if needs_vertical_trim:
		return CutDirection.VERTICAL
	if needs_horizontal_trim:
		return CutDirection.HORIZONTAL

	return None


def _collect_cycle_outputs(
	node: CutNode,
	node_path: str,
	direction: CutDirection,
) -> list[_TreeOutput]:
	if node.cut is None or node.cut.direction != direction:
		return [_TreeOutput(node=node, path=node_path)]

	if node.first is None or node.second is None:
		raise ValueError("Узел с линией реза должен содержать обе дочерние области.")

	return [
		*_collect_cycle_outputs(node.first, f"{node_path}.first", direction),
		*_collect_cycle_outputs(node.second, f"{node_path}.second", direction),
	]


def _trim_terminal_waste_outputs(outputs: list[_TreeOutput]) -> list[_TreeOutput]:
	useful_indexes = [
		index
		for index, output in enumerate(outputs)
		if _contains_part(output.node)
	]
	if not useful_indexes:
		return []

	return outputs[min(useful_indexes) : max(useful_indexes) + 1]


def _contains_part(node: CutNode) -> bool:
	if node.part_number is not None:
		return True

	return (
		(node.first is not None and _contains_part(node.first))
		or (node.second is not None and _contains_part(node.second))
	)


def _project_output_area(
	*,
	output_area: RectArea,
	source_area: RectArea,
	direction: CutDirection,
) -> RectArea:
	if direction == CutDirection.VERTICAL:
		return RectArea(
			x_mm=output_area.x_mm,
			y_mm=source_area.y_mm,
			width_mm=output_area.width_mm,
			height_mm=source_area.height_mm,
		)

	return RectArea(
		x_mm=source_area.x_mm,
		y_mm=output_area.y_mm,
		width_mm=source_area.width_mm,
		height_mm=output_area.height_mm,
	)


def _opposite_direction(direction: CutDirection) -> CutDirection:
	if direction == CutDirection.VERTICAL:
		return CutDirection.HORIZONTAL

	return CutDirection.VERTICAL


def _calculate_plan_metrics(
	*,
	cycles: tuple[CuttingCycle, ...],
	strip_turns: tuple[StripTurnEvent, ...],
	size_settings: tuple[SizeSettingEvent, ...],
) -> ProductionCutPlanMetrics:
	return ProductionCutPlanMetrics(
		cycle_count=len(cycles),
		strip_turn_count=len(strip_turns),
		size_setting_count=len(size_settings),
		pass_count=sum(cycle.metrics.pass_count for cycle in cycles),
		cut_length_mm=sum(cycle.metrics.cut_length_mm for cycle in cycles),
		nominal_cut_area_mm2=sum(cycle.metrics.nominal_cut_area_mm2 for cycle in cycles),
		actual_removed_area_mm2=sum(cycle.metrics.actual_removed_area_mm2 for cycle in cycles),
	)


def _contains_area(container: RectArea, area: RectArea, tolerance_mm: float) -> bool:
	return (
		area.x_mm >= container.x_mm - tolerance_mm
		and area.y_mm >= container.y_mm - tolerance_mm
		and area.right_mm <= container.right_mm + tolerance_mm
		and area.bottom_mm <= container.bottom_mm + tolerance_mm
	)
