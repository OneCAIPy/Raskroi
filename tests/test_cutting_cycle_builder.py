import pytest

from cutting_app.app.domain.cut_tree import CutDirection, RectArea
from cutting_app.app.domain.production_cut_plan import (
	CuttingCycleOutput,
	SawPassType,
)
from cutting_app.app.services.cutting_cycle_builder import build_parallel_cutting_cycle


def _output(
	output_id: str,
	x_mm: float,
	y_mm: float,
	width_mm: float,
	height_mm: float,
) -> CuttingCycleOutput:
	return CuttingCycleOutput(
		output_id=output_id,
		area=RectArea(
			x_mm=x_mm,
			y_mm=y_mm,
			width_mm=width_mm,
			height_mm=height_mm,
		),
	)


def test_cycle_adds_start_trim_when_first_output_has_leading_allowance():
	cycle = build_parallel_cutting_cycle(
		cycle_id="sheet-1",
		source_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=200),
		direction=CutDirection.VERTICAL,
		outputs=[_output("strip-1", 10, 0, 90, 200)],
		nominal_kerf_width_mm=4,
	)

	assert len(cycle.saw_passes) == 1

	saw_pass = cycle.saw_passes[0]

	assert saw_pass.sequence_number == 1
	assert saw_pass.pass_type == SawPassType.START_TRIM
	assert saw_pass.after_output_id is None
	assert saw_pass.x1_mm == 10
	assert saw_pass.y1_mm == 0
	assert saw_pass.x2_mm == 10
	assert saw_pass.y2_mm == 200
	assert saw_pass.length_mm == 200
	assert saw_pass.nominal_kerf_width_mm == 4
	assert saw_pass.actual_removed_width_mm == 4


def test_cycle_does_not_trim_already_formed_leading_or_trailing_edge():
	cycle = build_parallel_cutting_cycle(
		cycle_id="strip-1",
		source_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=200),
		direction=CutDirection.VERTICAL,
		outputs=[
			_output("part-1", 0, 0, 48, 200),
			_output("part-2", 52, 0, 48, 200),
		],
		nominal_kerf_width_mm=4,
	)

	assert [saw_pass.pass_type for saw_pass in cycle.saw_passes] == [SawPassType.SPLIT]
	assert cycle.saw_passes[0].after_output_id == "part-1"


def test_terminal_trim_uses_nominal_kerf_for_report_and_actual_width_for_balance():
	cycle = build_parallel_cutting_cycle(
		cycle_id="strip-1",
		source_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100),
		direction=CutDirection.VERTICAL,
		outputs=[_output("part-1", 0, 0, 98, 100)],
		nominal_kerf_width_mm=4,
	)

	assert len(cycle.saw_passes) == 1

	saw_pass = cycle.saw_passes[0]

	assert saw_pass.pass_type == SawPassType.END_TRIM
	assert saw_pass.length_mm == 100
	assert saw_pass.nominal_kerf_width_mm == 4
	assert saw_pass.actual_removed_width_mm == 2
	assert saw_pass.nominal_cut_area_mm2 == 400
	assert saw_pass.actual_removed_area_mm2 == 200

	assert cycle.metrics.pass_count == 1
	assert cycle.metrics.cut_length_mm == 100
	assert cycle.metrics.nominal_cut_area_mm2 == 400
	assert cycle.metrics.actual_removed_area_mm2 == 200


def test_internal_gap_must_fit_the_full_nominal_kerf():
	with pytest.raises(ValueError, match="полной ширины пропила"):
		build_parallel_cutting_cycle(
			cycle_id="strip-1",
			source_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100),
			direction=CutDirection.VERTICAL,
			outputs=[
				_output("part-1", 0, 0, 49, 100),
				_output("part-2", 51, 0, 49, 100),
			],
			nominal_kerf_width_mm=4,
		)


def test_start_trim_must_fit_the_full_nominal_kerf():
	with pytest.raises(ValueError, match="начальной торцовки"):
		build_parallel_cutting_cycle(
			cycle_id="sheet-1",
			source_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100),
			direction=CutDirection.VERTICAL,
			outputs=[_output("part-1", 2, 0, 98, 100)],
			nominal_kerf_width_mm=4,
		)


def test_cycle_metrics_sum_start_split_and_end_passes():
	cycle = build_parallel_cutting_cycle(
		cycle_id="sheet-1",
		source_area=RectArea(x_mm=0, y_mm=0, width_mm=200, height_mm=100),
		direction=CutDirection.VERTICAL,
		outputs=[
			_output("strip-1", 10, 0, 50, 100),
			_output("strip-2", 64, 0, 50, 100),
		],
		nominal_kerf_width_mm=4,
	)

	assert [saw_pass.pass_type for saw_pass in cycle.saw_passes] == [
		SawPassType.START_TRIM,
		SawPassType.SPLIT,
		SawPassType.END_TRIM,
	]
	assert [saw_pass.sequence_number for saw_pass in cycle.saw_passes] == [1, 2, 3]
	assert cycle.metrics.pass_count == 3
	assert cycle.metrics.cut_length_mm == 300
	assert cycle.metrics.nominal_cut_area_mm2 == 1200
	assert cycle.metrics.actual_removed_area_mm2 == 1200


def test_horizontal_pass_uses_full_source_width():
	cycle = build_parallel_cutting_cycle(
		cycle_id="sheet-1",
		source_area=RectArea(x_mm=5, y_mm=10, width_mm=200, height_mm=100),
		direction=CutDirection.HORIZONTAL,
		outputs=[_output("strip-1", 5, 20, 200, 90)],
		nominal_kerf_width_mm=4,
	)

	saw_pass = cycle.saw_passes[0]

	assert saw_pass.pass_type == SawPassType.START_TRIM
	assert saw_pass.x1_mm == 5
	assert saw_pass.y1_mm == 20
	assert saw_pass.x2_mm == 205
	assert saw_pass.y2_mm == 20
	assert saw_pass.length_mm == 200
