from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.services.sheet_calculator import calculate_usable_sheet_area


def test_usable_sheet_area_without_margins_equals_sheet_size():
    sheet = SheetInput(
        name="Лист 2800x2070",
        width_mm=2800,
        height_mm=2070,
    )

    area = calculate_usable_sheet_area(sheet)

    assert area.x_mm == 0
    assert area.y_mm == 0
    assert area.width_mm == 2800
    assert area.height_mm == 2070


def test_usable_sheet_area_respects_sheet_margins():
    sheet = SheetInput(
        name="Лист 2800x2070",
        width_mm=2800,
        height_mm=2070,
        margins=SheetMargins(
            left_mm=10,
            top_mm=20,
            right_mm=10,
            bottom_mm=20,
        ),
    )

    area = calculate_usable_sheet_area(sheet)

    assert area.x_mm == 10
    assert area.y_mm == 20
    assert area.width_mm == 2780
    assert area.height_mm == 2030


def test_different_sheets_can_have_different_sizes_and_margins():
    standard_sheet = SheetInput(
        name="Стандартный лист",
        width_mm=2800,
        height_mm=2070,
        margins=SheetMargins(left_mm=10, right_mm=10),
    )

    remnant = SheetInput(
        name="Остаток",
        width_mm=900,
        height_mm=600,
        is_remnant=True,
        margins=SheetMargins(
            left_mm=5,
            top_mm=5,
            right_mm=5,
            bottom_mm=5,
        ),
    )

    standard_area = calculate_usable_sheet_area(standard_sheet)
    remnant_area = calculate_usable_sheet_area(remnant)

    assert standard_area.width_mm == 2780
    assert standard_area.height_mm == 2070

    assert remnant_area.width_mm == 890
    assert remnant_area.height_mm == 590