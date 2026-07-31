from cutting_app.app.domain.cut_tree import CutDirection, RectArea
from cutting_app.app.domain.production_cut_plan import (
	CuttingCycle,
	CuttingCycleOutput,
	SawPassType,
)
from cutting_app.app.services.cutting_cycle_builder import build_parallel_cutting_cycle
from cutting_app.app.services.size_setting_event_builder import (
	build_size_setting_events,
)


_KERF_MM = 4

# Для каждой карты перечислены циклы в производственном порядке.
# Первый элемент цикла показывает наличие начальной торцовки, второй содержит
# последовательность устанавливаемых размеров. Фикстура извлечена из дерева
# эталонного заказа БАЗИС «Для Саши 23,07» и не содержит номеров деталей.
_BASIS_AGT_3019_SIZE_CYCLES = (
	(
		(True, (2396, 361)),
		(True, (288, 288, 596)),
		(False, (359,)),
		(True, (596, 596)),
	),
	(
		(True, (2296, 467)),
		(True, (753, 400)),
		(False, (263, 196)),
		(False, (396,)),
		(True, (491, 491, 199)),
	),
	(
		(True, (2296, 467)),
		(True, (753, 400)),
		(False, (263, 196)),
		(False, (396,)),
		(True, (491, 491, 99, 99)),
		(False, (749, 596, 596)),
	),
	(
		(True, (2286, 474)),
		(True, (971, 196)),
		(False, (396,)),
		(True, (492, 491, 199)),
		(False, (749, 596, 396, 396)),
		(False, (196,)),
		(False, (196,)),
	),
	(
		(True, (2286, 474)),
		(True, (482, 693)),
		(False, (431,)),
		(True, (492, 492, 199)),
		(False, (2109,)),
	),
	(
		(True, (96, 99, 971)),
		(True, (1999, 499)),
		(True, (2286,)),
		(True, (596, 596, 596, 596, 346)),
	),
	(
		(True, (1796, 939)),
		(True, (299, 682, 196)),
		(False, (396,)),
		(False, (482, 425)),
		(True, (399, 767)),
		(False, (1313, 431)),
		(False, (693,)),
	),
	(
		(True, (2042, 596)),
		(True, (525, 492)),
		(True, (579, 579)),
	),
	(
		(True, (1699, 529, 515)),
		(True, (359, 359)),
		(True, (358, 358, 358)),
		(True, (596, 596)),
		(False, (482, 482, 359, 359)),
	),
	(
		(True, (2286, 446)),
		(True, (749, 396)),
		(False, (196, 196)),
		(True, (525, 492, 164)),
		(False, (299, 596)),
		(False, (149,)),
	),
	(
		(True, (914, 596, 596, 596)),
		(True, (482, 482)),
		(True, (491, 491)),
		(True, (491, 491)),
		(True, (559, 559)),
	),
	(
		(True, (1600, 971)),
		(True, (346, 749)),
		(False, (596, 359)),
		(False, (596,)),
		(True, (309, 800)),
		(False, (400, 400, 767)),
		(False, (513, 263)),
		(False, (764,)),
	),
	(
		(True, (1299, 596, 596)),
		(True, (492, 491)),
		(True, (492, 492)),
		(True, (449, 696)),
		(False, (482, 758)),
		(False, (257, 426)),
		(False, (693,)),
	),
)


def test_equal_consecutive_outputs_reuse_one_size_setting():
	cycles = (
		_make_cycle(
			plan_id="sheet-1",
			cycle_number=1,
			sizes_mm=(50, 50),
			has_start_trim=False,
		),
	)

	settings = build_size_setting_events(
		plan_id="sheet-1",
		cycles=cycles,
	)

	assert len(settings) == 1
	assert settings[0].event_id == "sheet-1:size-setting:1"
	assert settings[0].sequence_number == 1
	assert settings[0].cycle_id == "sheet-1:cycle:1"
	assert settings[0].output_id == "sheet-1:cycle:1:output:1"
	assert settings[0].direction == CutDirection.VERTICAL
	assert settings[0].size_mm == 50


def test_changed_output_size_creates_a_new_setting_event():
	cycles = (
		_make_cycle(
			plan_id="sheet-1",
			cycle_number=1,
			sizes_mm=(40, 50, 50, 40),
			has_start_trim=False,
		),
	)

	settings = build_size_setting_events(
		plan_id="sheet-1",
		cycles=cycles,
	)

	assert [setting.size_mm for setting in settings] == [40, 50, 40]
	assert [setting.sequence_number for setting in settings] == [1, 2, 3]


def test_horizontal_cycle_uses_output_height_as_the_setting_size():
	cycle = build_parallel_cutting_cycle(
		cycle_id="sheet-1:cycle:1",
		source_area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=100),
		direction=CutDirection.HORIZONTAL,
		outputs=[
			CuttingCycleOutput(
				output_id="sheet-1:cycle:1:output:1",
				area=RectArea(x_mm=0, y_mm=0, width_mm=100, height_mm=40),
			),
			CuttingCycleOutput(
				output_id="sheet-1:cycle:1:output:2",
				area=RectArea(x_mm=0, y_mm=44, width_mm=100, height_mm=40),
			),
		],
		nominal_kerf_width_mm=_KERF_MM,
	)

	settings = build_size_setting_events(
		plan_id="sheet-1",
		cycles=(cycle,),
	)

	assert len(settings) == 1
	assert settings[0].direction == CutDirection.HORIZONTAL
	assert settings[0].size_mm == 40


def test_start_trim_resets_the_retained_size_between_cycles():
	cycles = (
		_make_cycle(
			plan_id="sheet-1",
			cycle_number=1,
			sizes_mm=(50,),
			has_start_trim=False,
		),
		_make_cycle(
			plan_id="sheet-1",
			cycle_number=2,
			sizes_mm=(50,),
			has_start_trim=True,
		),
	)

	settings = build_size_setting_events(
		plan_id="sheet-1",
		cycles=cycles,
	)

	assert [setting.cycle_id for setting in settings] == [
		"sheet-1:cycle:1",
		"sheet-1:cycle:2",
	]
	assert [setting.size_mm for setting in settings] == [50, 50]


def test_cycle_without_start_trim_can_reuse_the_retained_size():
	cycles = (
		_make_cycle(
			plan_id="sheet-1",
			cycle_number=1,
			sizes_mm=(50,),
			has_start_trim=False,
		),
		_make_cycle(
			plan_id="sheet-1",
			cycle_number=2,
			sizes_mm=(50,),
			has_start_trim=False,
		),
	)

	settings = build_size_setting_events(
		plan_id="sheet-1",
		cycles=cycles,
	)

	assert len(settings) == 1
	assert settings[0].cycle_id == "sheet-1:cycle:1"


def test_output_without_a_rear_pass_does_not_require_a_size_setting():
	cycle = build_parallel_cutting_cycle(
		cycle_id="sheet-1:cycle:1",
		source_area=RectArea(x_mm=0, y_mm=0, width_mm=50, height_mm=100),
		direction=CutDirection.VERTICAL,
		outputs=[
			_output(
				output_id="sheet-1:cycle:1:output:1",
				x_mm=0,
				width_mm=50,
			),
		],
		nominal_kerf_width_mm=_KERF_MM,
	)

	assert cycle.saw_passes == ()
	assert build_size_setting_events(
		plan_id="sheet-1",
		cycles=(cycle,),
	) == ()


def test_basis_agt_3019_has_123_size_settings_with_per_layout_match():
	setting_counts: list[int] = []

	for layout_number, cycle_specs in enumerate(
		_BASIS_AGT_3019_SIZE_CYCLES,
		start=1,
	):
		plan_id = f"basis-layout-{layout_number}"
		cycles = tuple(
			_make_cycle(
				plan_id=plan_id,
				cycle_number=cycle_number,
				sizes_mm=sizes_mm,
				has_start_trim=has_start_trim,
			)
			for cycle_number, (has_start_trim, sizes_mm) in enumerate(
				cycle_specs,
				start=1,
			)
		)
		settings = build_size_setting_events(
			plan_id=plan_id,
			cycles=cycles,
		)
		setting_counts.append(len(settings))

	assert setting_counts == [6, 9, 11, 12, 8, 8, 13, 5, 8, 11, 6, 14, 12]
	assert sum(setting_counts) == 123


def _make_cycle(
	*,
	plan_id: str,
	cycle_number: int,
	sizes_mm: tuple[float, ...],
	has_start_trim: bool,
) -> CuttingCycle:
	cycle_id = f"{plan_id}:cycle:{cycle_number}"
	position_mm = 10 if has_start_trim else 0
	outputs = []

	for output_number, size_mm in enumerate(sizes_mm, start=1):
		outputs.append(
			_output(
				output_id=f"{cycle_id}:output:{output_number}",
				x_mm=position_mm,
				width_mm=size_mm,
			)
		)
		position_mm += size_mm + _KERF_MM

	last_output_end_mm = position_mm - _KERF_MM
	cycle = build_parallel_cutting_cycle(
		cycle_id=cycle_id,
		source_area=RectArea(
			x_mm=0,
			y_mm=0,
			width_mm=last_output_end_mm + 2,
			height_mm=100,
		),
		direction=CutDirection.VERTICAL,
		outputs=outputs,
		nominal_kerf_width_mm=_KERF_MM,
	)

	assert any(
		saw_pass.pass_type == SawPassType.START_TRIM
		for saw_pass in cycle.saw_passes
	) is has_start_trim

	return cycle


def _output(
	*,
	output_id: str,
	x_mm: float,
	width_mm: float,
) -> CuttingCycleOutput:
	return CuttingCycleOutput(
		output_id=output_id,
		area=RectArea(
			x_mm=x_mm,
			y_mm=0,
			width_mm=width_mm,
			height_mm=100,
		),
	)
