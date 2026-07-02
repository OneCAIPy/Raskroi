from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.services.validation_service import (
    validate_cut_settings,
    validate_sheet_input,
)


def test_valid_sheet_has_no_validation_issues():
    sheet = SheetInput(
        name="Лист 2800x2070",
        width_mm=2800,
        height_mm=2070,
        quantity=1,
    )

    issues = validate_sheet_input(sheet)

    assert issues == []


def test_sheet_margins_cannot_make_usable_width_negative():
    sheet = SheetInput(
        name="Плохой лист",
        width_mm=100,
        height_mm=100,
        margins=SheetMargins(
            left_mm=60,
            right_mm=60,
        ),
    )

    issues = validate_sheet_input(sheet)

    assert any(issue.code == "INVALID_USABLE_SHEET_WIDTH" for issue in issues)


def test_sheet_margins_cannot_make_usable_height_negative():
    sheet = SheetInput(
        name="Плохой лист",
        width_mm=100,
        height_mm=100,
        margins=SheetMargins(
            top_mm=60,
            bottom_mm=60,
        ),
    )

    issues = validate_sheet_input(sheet)

    assert any(issue.code == "INVALID_USABLE_SHEET_HEIGHT" for issue in issues)


def test_cut_settings_kerf_width_must_be_positive():
    settings = CutSettings(
        kerf_width_mm=0,
    )

    issues = validate_cut_settings(settings)

    assert len(issues) == 1
    assert issues[0].code == "INVALID_KERF_WIDTH"