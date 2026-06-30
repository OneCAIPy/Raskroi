from dataclasses import dataclass
from enum import Enum


class EdgeSide(str, Enum):
	L1 = "L1"
	L2 = "L2"
	W1 = "W1"
	W2 = "W2"


@dataclass(frozen=True)
class EdgeSpec:
	thickness_mm: float = 0.0
	trimming_allowance_mm: float = 0.0
	tape_overhang_mm: float = 0.0

	@property
	def has_edge(self) -> bool:
		return self.thickness_mm > 0


@dataclass(frozen=True)
class EdgeSet:
	L1: EdgeSpec = EdgeSpec()
	L2: EdgeSpec = EdgeSpec()
	W1: EdgeSpec = EdgeSpec()
	W2: EdgeSpec = EdgeSpec()

	def by_side(self, side: EdgeSide) -> EdgeSpec:
		return {
			EdgeSide.L1: self.L1,
			EdgeSide.L2: self.L2,
			EdgeSide.W1: self.W1,
			EdgeSide.W2: self.W2,
		}[side]