from dataclasses import dataclass
from enum import Enum


class CutDirection(str, Enum):
	VERTICAL = "vertical"
	HORIZONTAL = "horizontal"


@dataclass(frozen=True)
class RectArea:
	x_mm: float
	y_mm: float
	width_mm: float
	height_mm: float

	@property
	def right_mm(self) -> float:
		return self.x_mm + self.width_mm

	@property
	def bottom_mm(self) -> float:
		return self.y_mm + self.height_mm


@dataclass(frozen=True)
class CutLine:
	direction: CutDirection
	position_mm: float
	kerf_width_mm: float


@dataclass
class CutNode:
	area: RectArea
	cut: CutLine | None = None
	first: "CutNode | None" = None
	second: "CutNode | None" = None
	part_number: str | None = None
	is_waste: bool = False

	@property
	def is_leaf(self) -> bool:
		return self.cut is None and self.first is None and self.second is None
