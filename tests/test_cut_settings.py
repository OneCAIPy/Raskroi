from cutting_app.app.domain.cut_settings import CutSettings


def test_cut_settings_can_use_different_kerf_widths():
    narrow_saw = CutSettings(kerf_width_mm=3.2)
    standard_saw = CutSettings(kerf_width_mm=4.0)

    assert narrow_saw.kerf_width_mm == 3.2
    assert standard_saw.kerf_width_mm == 4.0