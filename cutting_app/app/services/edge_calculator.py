from cutting_app.app.domain.edge import EdgeSide
from cutting_app.app.domain.part import PartInput


def calculate_edge_length_mm(part: PartInput) -> float:
	total = 0.0

	if part.edges.L1.has_edge:
		total += part.l_mm

	if part.edges.L2.has_edge:
		total += part.l_mm

	if part.edges.W1.has_edge:
		total += part.w_mm

	if part.edges.W2.has_edge:
		total += part.w_mm

	return total