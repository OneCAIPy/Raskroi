from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cut_tree import CutDirection


def test_cut_settings_can_use_different_kerf_widths():
    narrow_saw = CutSettings(kerf_width_mm=3.2)
    standard_saw = CutSettings(kerf_width_mm=4.0)

    assert narrow_saw.kerf_width_mm == 3.2
    assert standard_saw.kerf_width_mm == 4.0


def test_cut_settings_use_explicit_initial_cut_direction():
	default_settings = CutSettings(kerf_width_mm=4)
	horizontal_first = CutSettings(
		kerf_width_mm=4,
		initial_cut_direction=CutDirection.HORIZONTAL,
	)

	assert default_settings.initial_cut_direction == CutDirection.VERTICAL
	assert horizontal_first.initial_cut_direction == CutDirection.HORIZONTAL
