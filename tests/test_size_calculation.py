from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.size_calculator import calculate_part_sizes


def test_edge_on_w_sides_reduces_l_dimension():
	part = PartInput(
		number="1",
		name="Полка",
		l_mm=397,
		w_mm=397,
		quantity=1,
		edges=EdgeSet(
			W1=EdgeSpec(thickness_mm=1, trimming_allowance_mm=0.5),
			W2=EdgeSpec(thickness_mm=1, trimming_allowance_mm=0.5),
		),
	)

	sizes = calculate_part_sizes(part)

	assert sizes.no_edge_l_mm == 395
	assert sizes.blank_l_mm == 396
	assert sizes.cutting_l_mm == 396
	assert sizes.no_edge_w_mm == 397
	assert sizes.blank_w_mm == 397
	assert sizes.cutting_w_mm == 397
	

def test_edge_on_l_sides_reduces_w_dimension():
	part = PartInput(
		number="2",
		name="Боковина",
		l_mm=800,
		w_mm=400,
		quantity=1,
		edges=EdgeSet(
			L1=EdgeSpec(thickness_mm=2, trimming_allowance_mm=0.5),
			L2=EdgeSpec(thickness_mm=2, trimming_allowance_mm=0.5),
		),
	)

	sizes = calculate_part_sizes(part)

	assert sizes.no_edge_l_mm == 800
	assert sizes.blank_l_mm == 800
	assert sizes.cutting_l_mm == 800

	assert sizes.no_edge_w_mm == 396
	assert sizes.blank_w_mm == 397
	assert sizes.cutting_w_mm == 397


def test_l_is_first_dimension_even_when_smaller_than_w():
    part = PartInput(
        number="3",
        name="Фасад",
        l_mm=300,
        w_mm=800,
        quantity=1,
        edges=EdgeSet(
            W1=EdgeSpec(thickness_mm=1, trimming_allowance_mm=0.5),
            W2=EdgeSpec(thickness_mm=1, trimming_allowance_mm=0.5),
        ),
    )

    sizes = calculate_part_sizes(part)

    assert sizes.final_l_mm == 300
    assert sizes.final_w_mm == 800

    assert sizes.no_edge_l_mm == 298
    assert sizes.blank_l_mm == 299
    assert sizes.cutting_l_mm == 299

    assert sizes.no_edge_w_mm == 800
    assert sizes.blank_w_mm == 800
    assert sizes.cutting_w_mm == 800