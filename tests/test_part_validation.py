from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.validation_service import validate_part_input


def test_valid_part_has_no_validation_issues():
    part = PartInput(
        number="1",
        name="Полка",
        l_mm=397,
        w_mm=397,
        quantity=1,
        edges=EdgeSet(),
    )

    issues = validate_part_input(part)

    assert issues == []


def test_part_with_zero_quantity_has_validation_issue():
    part = PartInput(
        number="1",
        name="Полка",
        l_mm=397,
        w_mm=397,
        quantity=0,
        edges=EdgeSet(),
    )

    issues = validate_part_input(part)

    assert len(issues) == 1
    assert issues[0].code == "INVALID_QUANTITY"


def test_edge_thickness_cannot_make_no_edge_l_size_negative():
    part = PartInput(
        number="1",
        name="Узкая деталь",
        l_mm=1,
        w_mm=100,
        quantity=1,
        edges=EdgeSet(
            W1=EdgeSpec(thickness_mm=1),
            W2=EdgeSpec(thickness_mm=1),
        ),
    )

    issues = validate_part_input(part)

    assert any(issue.code == "INVALID_NO_EDGE_L_SIZE" for issue in issues)


def test_edge_thickness_cannot_make_no_edge_w_size_negative():
    part = PartInput(
        number="1",
        name="Узкая деталь",
        l_mm=100,
        w_mm=1,
        quantity=1,
        edges=EdgeSet(
            L1=EdgeSpec(thickness_mm=1),
            L2=EdgeSpec(thickness_mm=1),
        ),
    )

    issues = validate_part_input(part)

    assert any(issue.code == "INVALID_NO_EDGE_W_SIZE" for issue in issues)