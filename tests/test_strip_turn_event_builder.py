from dataclasses import replace

import pytest

from cutting_app.app.domain.cut_tree import CutDirection, RectArea
from cutting_app.app.domain.production_cut_plan import (
	CuttingCycle,
	CuttingCycleMetrics,
	CuttingCycleOutput,
)
from cutting_app.app.services.strip_turn_event_builder import (
	build_strip_turn_events,
)


_REFERENCE_AREA = RectArea(
	x_mm=0,
	y_mm=0,
	width_mm=100,
	height_mm=100,
)
_ZERO_CYCLE_METRICS = CuttingCycleMetrics(
	pass_count=0,
	cut_length_mm=0,
	nominal_cut_area_mm2=0,
	actual_removed_area_mm2=0,
)

# Иерархия циклов извлечена из 13 Layout эталонного заказа БАЗИС
# «Для Саши 23,07». Индекс задаёт цикл, значение — индекс его родителя.
# В фикстуре нет клиентских данных, размеров и номеров деталей.
_BASIS_AGT_3019_CYCLE_PARENTS = (
	(None, 0, 1, 0),
	(None, 0, 1, 2, 0),
	(None, 0, 1, 2, 0, 4),
	(None, 0, 1, 0, 3, 4, 4),
	(None, 0, 1, 0, 3),
	(None, 0, 0, 0),
	(None, 0, 1, 1, 0, 4, 5),
	(None, 0, 0),
	(None, 0, 0, 0, 3),
	(None, 0, 1, 0, 3, 4),
	(None, 0, 0, 0, 0),
	(None, 0, 1, 2, 0, 4, 5, 6),
	(None, 0, 0, 0, 3, 4, 5),
)


def test_nested_cycle_creates_linked_quarter_turn_event():
	cycles = _make_linked_cycles(
		plan_id="sheet-1",
		parent_indexes=(None, 0),
	)

	turns = build_strip_turn_events(
		plan_id="sheet-1",
		cycles=cycles,
	)

	assert len(turns) == 1

	turn = turns[0]
	parent_cycle, child_cycle = cycles

	assert turn.event_id == "sheet-1:turn:1"
	assert turn.sequence_number == 1
	assert turn.source_output_id == child_cycle.source_output_id
	assert turn.source_area == child_cycle.source_area
	assert turn.from_cycle_id == parent_cycle.cycle_id
	assert turn.to_cycle_id == child_cycle.cycle_id
	assert turn.from_direction == CutDirection.VERTICAL
	assert turn.to_direction == CutDirection.HORIZONTAL
	assert turn.angle_degrees == 90


def test_root_cycle_does_not_create_strip_turn_event():
	cycles = _make_linked_cycles(
		plan_id="sheet-1",
		parent_indexes=(None,),
	)

	turns = build_strip_turn_events(
		plan_id="sheet-1",
		cycles=cycles,
	)

	assert turns == ()


def test_nested_cycle_with_same_direction_is_rejected():
	cycles = _make_linked_cycles(
		plan_id="sheet-1",
		parent_indexes=(None, 0),
	)
	cycles = (
		cycles[0],
		replace(cycles[1], direction=cycles[0].direction),
	)

	with pytest.raises(ValueError, match="перпендикулярн"):
		build_strip_turn_events(
			plan_id="sheet-1",
			cycles=cycles,
		)


def test_basis_agt_3019_hierarchy_has_59_strip_turns():
	turn_counts: list[int] = []
	cycle_count = 0

	for layout_number, parent_indexes in enumerate(
		_BASIS_AGT_3019_CYCLE_PARENTS,
		start=1,
	):
		plan_id = f"basis-layout-{layout_number}"
		cycles = _make_linked_cycles(
			plan_id=plan_id,
			parent_indexes=parent_indexes,
		)
		turns = build_strip_turn_events(
			plan_id=plan_id,
			cycles=cycles,
		)

		turn_counts.append(len(turns))
		cycle_count += len(cycles)

	assert turn_counts == [3, 4, 5, 6, 4, 3, 6, 2, 4, 5, 4, 7, 6]
	assert cycle_count == 72
	assert sum(turn_counts) == 59


def _make_linked_cycles(
	*,
	plan_id: str,
	parent_indexes: tuple[int | None, ...],
) -> tuple[CuttingCycle, ...]:
	if not parent_indexes or parent_indexes[0] is not None:
		raise ValueError("Первый цикл фикстуры должен быть корневым.")

	cycle_ids = [
		f"{plan_id}:cycle:{index + 1}"
		for index in range(len(parent_indexes))
	]
	source_output_ids: dict[int, str] = {}
	children_by_parent: dict[int, list[int]] = {
		index: []
		for index in range(len(parent_indexes))
	}
	depths = [0] * len(parent_indexes)

	for child_index, parent_index in enumerate(parent_indexes):
		if parent_index is None:
			continue

		source_output_ids[child_index] = (
			f"{cycle_ids[parent_index]}:output-for:{child_index + 1}"
		)
		children_by_parent[parent_index].append(child_index)
		depths[child_index] = depths[parent_index] + 1

	cycles: list[CuttingCycle] = []

	for cycle_index, parent_index in enumerate(parent_indexes):
		cycle_id = cycle_ids[cycle_index]
		outputs = tuple(
			CuttingCycleOutput(
				output_id=source_output_ids[child_index],
				area=_REFERENCE_AREA,
			)
			for child_index in children_by_parent[cycle_index]
		)
		if not outputs:
			outputs = (
				CuttingCycleOutput(
					output_id=f"{cycle_id}:finished-part",
					area=_REFERENCE_AREA,
					part_number=str(cycle_index + 1),
				),
			)

		direction = (
			CutDirection.VERTICAL
			if depths[cycle_index] % 2 == 0
			else CutDirection.HORIZONTAL
		)
		cycles.append(
			CuttingCycle(
				cycle_id=cycle_id,
				source_area=_REFERENCE_AREA,
				direction=direction,
				outputs=outputs,
				saw_passes=(),
				metrics=_ZERO_CYCLE_METRICS,
				parent_cycle_id=(
					None
					if parent_index is None
					else cycle_ids[parent_index]
				),
				source_output_id=source_output_ids.get(cycle_index),
			)
		)

	return tuple(cycles)
