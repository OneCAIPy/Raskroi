from cutting_app.app.domain.edge import EdgeSide
from cutting_app.app.domain.part import PartInput


def calculate_edge_length_mm(part: PartInput) -> float:
	return sum(
		calculate_edge_side_length_mm(part, side)
		for side in EdgeSide
		if part.edges.by_side(side).has_edge
	)


def calculate_edge_side_length_mm(part: PartInput, side: EdgeSide) -> float:
	if side in (EdgeSide.L1, EdgeSide.L2):
		return part.l_mm

	return part.w_mm
