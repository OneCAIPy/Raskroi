from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.edge_calculator import calculate_edge_length_mm


def test_edge_length_uses_logical_l_and_w_dimensions():
	part = PartInput(
		number="1",
		name="Фасад",
		l_mm=300,
		w_mm=800,
		quantity=1,
		edges=EdgeSet(
			L1=EdgeSpec(thickness_mm=1),
			L2=EdgeSpec(thickness_mm=1),
			W1=EdgeSpec(thickness_mm=1),
		),
	)

	assert calculate_edge_length_mm(part) == 1400