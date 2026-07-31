from cutting_app.app.domain.cut_tree import CutDirection, RectArea
from cutting_app.app.domain.production_cut_plan import (
	CuttingCycle,
	SawPassType,
	SizeSettingEvent,
)


def build_size_setting_events(
	*,
	plan_id: str,
	cycles: tuple[CuttingCycle, ...],
	tolerance_mm: float = 0.001,
) -> tuple[SizeSettingEvent, ...]:
	_validate_input(
		plan_id=plan_id,
		cycles=cycles,
		tolerance_mm=tolerance_mm,
	)

	settings: list[SizeSettingEvent] = []
	retained_size_mm: float | None = None

	for cycle in cycles:
		outputs_by_id = {
			output.output_id: output
			for output in cycle.outputs
		}
		start_trim_seen = False
		output_pass_seen = False

		for saw_pass in cycle.saw_passes:
			if saw_pass.pass_type == SawPassType.START_TRIM:
				if start_trim_seen or output_pass_seen:
					raise ValueError(
						"Начальная торцовка должна быть единственным первым проходом цикла."
					)
				if saw_pass.after_output_id is not None:
					raise ValueError(
						"Начальная торцовка не должна ссылаться на выход цикла."
					)

				start_trim_seen = True
				retained_size_mm = None
				continue

			output_pass_seen = True
			if saw_pass.after_output_id is None:
				raise ValueError(
					"Разделительный или конечный проход должен ссылаться на выход цикла."
				)

			output = outputs_by_id.get(saw_pass.after_output_id)
			if output is None:
				raise ValueError(
					"Выход для установки размера отсутствует в цикле пиления."
				)

			size_mm = _cutting_size_mm(
				area=output.area,
				direction=cycle.direction,
			)
			if (
				retained_size_mm is not None
				and abs(size_mm - retained_size_mm) <= tolerance_mm
			):
				continue

			settings.append(
				SizeSettingEvent(
					event_id=f"{plan_id}:size-setting:{len(settings) + 1}",
					sequence_number=len(settings) + 1,
					cycle_id=cycle.cycle_id,
					output_id=output.output_id,
					direction=cycle.direction,
					size_mm=size_mm,
				)
			)
			retained_size_mm = size_mm

	return tuple(settings)


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

	output_ids: list[str] = []
	for cycle in cycles:
		cycle_output_ids = [output.output_id for output in cycle.outputs]
		if any(not output_id.strip() for output_id in cycle_output_ids):
			raise ValueError("Идентификатор выхода цикла не должен быть пустым.")

		if len(set(cycle_output_ids)) != len(cycle_output_ids):
			raise ValueError("Идентификаторы выходов одного цикла не должны повторяться.")

		for saw_pass in cycle.saw_passes:
			if saw_pass.cycle_id != cycle.cycle_id:
				raise ValueError("Физический проход связан с другим циклом пиления.")

		output_ids.extend(cycle_output_ids)

	if len(set(output_ids)) != len(output_ids):
		raise ValueError("Идентификаторы выходов одного плана не должны повторяться.")


def _cutting_size_mm(*, area: RectArea, direction: CutDirection) -> float:
	if direction == CutDirection.VERTICAL:
		return area.width_mm

	return area.height_mm
