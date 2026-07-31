from cutting_app.app.domain.production_cut_plan import (
	CuttingCycle,
	CuttingCycleOutput,
	StripTurnEvent,
)


def build_strip_turn_events(
	*,
	plan_id: str,
	cycles: tuple[CuttingCycle, ...],
	tolerance_mm: float = 0.001,
) -> tuple[StripTurnEvent, ...]:
	_validate_input(
		plan_id=plan_id,
		cycles=cycles,
		tolerance_mm=tolerance_mm,
	)

	if not cycles:
		return ()

	cycles_by_id = {
		cycle.cycle_id: cycle
		for cycle in cycles
	}
	cycle_indexes = {
		cycle.cycle_id: index
		for index, cycle in enumerate(cycles)
	}
	turns: list[StripTurnEvent] = []

	for cycle in cycles:
		if cycle.parent_cycle_id is None:
			continue

		parent_cycle = cycles_by_id.get(cycle.parent_cycle_id)
		if parent_cycle is None:
			raise ValueError(
				"Родительский цикл события поворота отсутствует в производственном плане."
			)

		if cycle_indexes[parent_cycle.cycle_id] >= cycle_indexes[cycle.cycle_id]:
			raise ValueError(
				"Родительский цикл должен находиться раньше вложенного цикла."
			)

		if cycle.source_output_id is None:
			raise ValueError(
				"Вложенный цикл должен ссылаться на выход родительского цикла."
			)

		source_output = _find_source_output(
			parent_cycle=parent_cycle,
			source_output_id=cycle.source_output_id,
		)
		if not _areas_match(
			source_output=source_output,
			cycle=cycle,
			tolerance_mm=tolerance_mm,
		):
			raise ValueError(
				"Область вложенного цикла не совпадает с выходом родительского цикла."
			)

		if parent_cycle.direction == cycle.direction:
			raise ValueError(
				"Вложенный цикл должен иметь направление, перпендикулярное родительскому."
			)

		turns.append(
			StripTurnEvent(
				event_id=f"{plan_id}:turn:{len(turns) + 1}",
				sequence_number=len(turns) + 1,
				source_output_id=source_output.output_id,
				source_area=cycle.source_area,
				from_cycle_id=parent_cycle.cycle_id,
				to_cycle_id=cycle.cycle_id,
				from_direction=parent_cycle.direction,
				to_direction=cycle.direction,
			)
		)

	return tuple(turns)


def _validate_input(
	*,
	plan_id: str,
	cycles: tuple[CuttingCycle, ...],
	tolerance_mm: float,
) -> None:
	if not plan_id.strip():
		raise ValueError("Идентификатор производственного плана не должен быть пустым.")

	if tolerance_mm < 0:
		raise ValueError("Допуск сравнения не может быть отрицательным.")

	cycle_ids = [cycle.cycle_id for cycle in cycles]
	if any(not cycle_id.strip() for cycle_id in cycle_ids):
		raise ValueError("Идентификатор цикла пиления не должен быть пустым.")

	if len(set(cycle_ids)) != len(cycle_ids):
		raise ValueError("Идентификаторы циклов одного плана не должны повторяться.")

	root_cycles = [
		cycle
		for cycle in cycles
		if cycle.parent_cycle_id is None
	]
	if cycles and len(root_cycles) != 1:
		raise ValueError(
			"Производственный план одного листа должен содержать один корневой цикл."
		)

	for cycle in root_cycles:
		if cycle.source_output_id is not None:
			raise ValueError(
				"Корневой цикл не должен ссылаться на выход родительского цикла."
			)


def _find_source_output(
	*,
	parent_cycle: CuttingCycle,
	source_output_id: str,
) -> CuttingCycleOutput:
	for output in parent_cycle.outputs:
		if output.output_id == source_output_id:
			return output

	raise ValueError(
		"Выход родительского цикла для поворачиваемой полосы не найден."
	)


def _areas_match(
	*,
	source_output: CuttingCycleOutput,
	cycle: CuttingCycle,
	tolerance_mm: float,
) -> bool:
	return (
		abs(source_output.area.x_mm - cycle.source_area.x_mm) <= tolerance_mm
		and abs(source_output.area.y_mm - cycle.source_area.y_mm) <= tolerance_mm
		and abs(source_output.area.width_mm - cycle.source_area.width_mm) <= tolerance_mm
		and abs(source_output.area.height_mm - cycle.source_area.height_mm) <= tolerance_mm
	)
