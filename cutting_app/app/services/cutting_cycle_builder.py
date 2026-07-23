from cutting_app.app.domain.cut_tree import CutDirection, RectArea
from cutting_app.app.domain.production_cut_plan import (
	CuttingCycle,
	CuttingCycleMetrics,
	CuttingCycleOutput,
	SawPass,
	SawPassType,
)


def build_parallel_cutting_cycle(
	*,
	cycle_id: str,
	source_area: RectArea,
	direction: CutDirection,
	outputs: list[CuttingCycleOutput],
	nominal_kerf_width_mm: float,
	tolerance_mm: float = 0.001,
) -> CuttingCycle:
	_validate_cycle_input(
		cycle_id=cycle_id,
		source_area=source_area,
		outputs=outputs,
		nominal_kerf_width_mm=nominal_kerf_width_mm,
		tolerance_mm=tolerance_mm,
	)

	sorted_outputs = tuple(sorted(outputs, key=lambda output: _output_sort_key(output, direction)))
	_validate_outputs(
		source_area=source_area,
		direction=direction,
		outputs=sorted_outputs,
		nominal_kerf_width_mm=nominal_kerf_width_mm,
		tolerance_mm=tolerance_mm,
	)

	saw_passes = _build_saw_passes(
		cycle_id=cycle_id,
		source_area=source_area,
		direction=direction,
		outputs=sorted_outputs,
		nominal_kerf_width_mm=nominal_kerf_width_mm,
		tolerance_mm=tolerance_mm,
	)

	return CuttingCycle(
		cycle_id=cycle_id,
		source_area=source_area,
		direction=direction,
		outputs=sorted_outputs,
		saw_passes=saw_passes,
		metrics=_calculate_cycle_metrics(saw_passes),
	)


def _validate_cycle_input(
	*,
	cycle_id: str,
	source_area: RectArea,
	outputs: list[CuttingCycleOutput],
	nominal_kerf_width_mm: float,
	tolerance_mm: float,
) -> None:
	if not cycle_id.strip():
		raise ValueError("Идентификатор цикла пиления не должен быть пустым.")

	if source_area.width_mm <= 0 or source_area.height_mm <= 0:
		raise ValueError("Исходная область цикла пиления должна иметь положительные размеры.")

	if nominal_kerf_width_mm <= 0:
		raise ValueError("Номинальная ширина пропила должна быть положительной.")

	if tolerance_mm < 0:
		raise ValueError("Допуск сравнения не может быть отрицательным.")

	if not outputs:
		raise ValueError("Цикл пиления должен содержать хотя бы один выходной элемент.")

	output_ids = [output.output_id for output in outputs]
	if any(not output_id.strip() for output_id in output_ids):
		raise ValueError("Идентификатор выходного элемента не должен быть пустым.")

	if len(set(output_ids)) != len(output_ids):
		raise ValueError("Идентификаторы выходных элементов одного цикла не должны повторяться.")


def _validate_outputs(
	*,
	source_area: RectArea,
	direction: CutDirection,
	outputs: tuple[CuttingCycleOutput, ...],
	nominal_kerf_width_mm: float,
	tolerance_mm: float,
) -> None:
	for output in outputs:
		if output.area.width_mm <= 0 or output.area.height_mm <= 0:
			raise ValueError("Выходной элемент цикла пиления должен иметь положительные размеры.")

		if not _contains_area(source_area, output.area, tolerance_mm):
			raise ValueError("Выходной элемент выходит за исходную область цикла пиления.")

		if not _spans_transverse_axis(source_area, output.area, direction, tolerance_mm):
			raise ValueError(
				"Выходной элемент одного параллельного цикла должен занимать весь поперечный размер исходной области."
			)

	leading_gap_mm = _axis_start(outputs[0].area, direction) - _axis_start(source_area, direction)
	if tolerance_mm < leading_gap_mm < nominal_kerf_width_mm - tolerance_mm:
		raise ValueError("Для начальной торцовки недостаточно полной ширины пропила.")

	for current, following in zip(outputs, outputs[1:]):
		gap_mm = _axis_start(following.area, direction) - _axis_end(current.area, direction)

		if abs(gap_mm - nominal_kerf_width_mm) <= tolerance_mm:
			continue

		raise ValueError(
			"Между соседними выходами одного цикла не хватает полной ширины пропила."
		)


def _build_saw_passes(
	*,
	cycle_id: str,
	source_area: RectArea,
	direction: CutDirection,
	outputs: tuple[CuttingCycleOutput, ...],
	nominal_kerf_width_mm: float,
	tolerance_mm: float,
) -> tuple[SawPass, ...]:
	saw_passes: list[SawPass] = []
	source_start_mm = _axis_start(source_area, direction)
	source_end_mm = _axis_end(source_area, direction)
	first_start_mm = _axis_start(outputs[0].area, direction)
	leading_gap_mm = first_start_mm - source_start_mm

	if leading_gap_mm > tolerance_mm:
		saw_passes.append(
			_make_saw_pass(
				cycle_id=cycle_id,
				sequence_number=len(saw_passes) + 1,
				pass_type=SawPassType.START_TRIM,
				direction=direction,
				position_mm=first_start_mm,
				source_area=source_area,
				nominal_kerf_width_mm=nominal_kerf_width_mm,
				actual_removed_width_mm=nominal_kerf_width_mm,
			)
		)

	for index, output in enumerate(outputs):
		output_end_mm = _axis_end(output.area, direction)
		is_last_output = index == len(outputs) - 1

		if not is_last_output:
			following_start_mm = _axis_start(outputs[index + 1].area, direction)
			actual_gap_mm = following_start_mm - output_end_mm
			saw_passes.append(
				_make_saw_pass(
					cycle_id=cycle_id,
					sequence_number=len(saw_passes) + 1,
					pass_type=SawPassType.SPLIT,
					direction=direction,
					position_mm=output_end_mm,
					source_area=source_area,
					nominal_kerf_width_mm=nominal_kerf_width_mm,
					actual_removed_width_mm=actual_gap_mm,
					after_output_id=output.output_id,
				)
			)
			continue

		trailing_gap_mm = source_end_mm - output_end_mm
		if trailing_gap_mm <= tolerance_mm:
			continue

		saw_passes.append(
			_make_saw_pass(
				cycle_id=cycle_id,
				sequence_number=len(saw_passes) + 1,
				pass_type=SawPassType.END_TRIM,
				direction=direction,
				position_mm=output_end_mm,
				source_area=source_area,
				nominal_kerf_width_mm=nominal_kerf_width_mm,
				actual_removed_width_mm=min(nominal_kerf_width_mm, trailing_gap_mm),
				after_output_id=output.output_id,
			)
		)

	return tuple(saw_passes)


def _make_saw_pass(
	*,
	cycle_id: str,
	sequence_number: int,
	pass_type: SawPassType,
	direction: CutDirection,
	position_mm: float,
	source_area: RectArea,
	nominal_kerf_width_mm: float,
	actual_removed_width_mm: float,
	after_output_id: str | None = None,
) -> SawPass:
	if direction == CutDirection.VERTICAL:
		return SawPass(
			cycle_id=cycle_id,
			sequence_number=sequence_number,
			pass_type=pass_type,
			direction=direction,
			x1_mm=position_mm,
			y1_mm=source_area.y_mm,
			x2_mm=position_mm,
			y2_mm=source_area.bottom_mm,
			nominal_kerf_width_mm=nominal_kerf_width_mm,
			actual_removed_width_mm=actual_removed_width_mm,
			after_output_id=after_output_id,
		)

	return SawPass(
		cycle_id=cycle_id,
		sequence_number=sequence_number,
		pass_type=pass_type,
		direction=direction,
		x1_mm=source_area.x_mm,
		y1_mm=position_mm,
		x2_mm=source_area.right_mm,
		y2_mm=position_mm,
		nominal_kerf_width_mm=nominal_kerf_width_mm,
		actual_removed_width_mm=actual_removed_width_mm,
		after_output_id=after_output_id,
	)


def _calculate_cycle_metrics(saw_passes: tuple[SawPass, ...]) -> CuttingCycleMetrics:
	return CuttingCycleMetrics(
		pass_count=len(saw_passes),
		cut_length_mm=sum(saw_pass.length_mm for saw_pass in saw_passes),
		nominal_cut_area_mm2=sum(saw_pass.nominal_cut_area_mm2 for saw_pass in saw_passes),
		actual_removed_area_mm2=sum(saw_pass.actual_removed_area_mm2 for saw_pass in saw_passes),
	)


def _output_sort_key(output: CuttingCycleOutput, direction: CutDirection) -> tuple[float, str]:
	return (_axis_start(output.area, direction), output.output_id)


def _axis_start(area: RectArea, direction: CutDirection) -> float:
	if direction == CutDirection.VERTICAL:
		return area.x_mm

	return area.y_mm


def _axis_end(area: RectArea, direction: CutDirection) -> float:
	if direction == CutDirection.VERTICAL:
		return area.right_mm

	return area.bottom_mm


def _contains_area(container: RectArea, area: RectArea, tolerance_mm: float) -> bool:
	return (
		area.x_mm >= container.x_mm - tolerance_mm
		and area.y_mm >= container.y_mm - tolerance_mm
		and area.right_mm <= container.right_mm + tolerance_mm
		and area.bottom_mm <= container.bottom_mm + tolerance_mm
	)


def _spans_transverse_axis(
	source_area: RectArea,
	output_area: RectArea,
	direction: CutDirection,
	tolerance_mm: float,
) -> bool:
	if direction == CutDirection.VERTICAL:
		return (
			abs(output_area.y_mm - source_area.y_mm) <= tolerance_mm
			and abs(output_area.bottom_mm - source_area.bottom_mm) <= tolerance_mm
		)

	return (
		abs(output_area.x_mm - source_area.x_mm) <= tolerance_mm
		and abs(output_area.right_mm - source_area.right_mm) <= tolerance_mm
	)
