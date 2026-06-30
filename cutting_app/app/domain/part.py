from dataclasses import dataclass

from cutting_app.app.domain.edge import EdgeSet


@dataclass(frozen=True)
class PartInput:
	number: str
	name: str
	l_mm: float
	w_mm: float
	quantity: int
	edges: EdgeSet
	rotation_allowed: bool = True


@dataclass(frozen=True)
class PartSizes:
	final_l_mm: float
	final_w_mm: float

	no_edge_l_mm: float
	no_edge_w_mm: float

	blank_l_mm: float
	blank_w_mm: float

	cutting_l_mm: float
	cutting_w_mm: float