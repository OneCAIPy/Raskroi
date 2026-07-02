from dataclasses import dataclass, field

from cutting_app.app.domain.cut_tree import CutDirection, CutNode, RectArea
from cutting_app.app.domain.placement import Rotation


@dataclass(frozen=True)
class PlacedPart:
	part_number: str
	source_part_number: str
	part_name: str
	sheet_name: str
	x_mm: float
	y_mm: float
	width_mm: float
	height_mm: float
	rotation: Rotation


@dataclass(frozen=True)
class UnplacedPart:
	part_number: str
	source_part_number: str
	part_name: str
	reason_code: str
	reason: str


@dataclass(frozen=True)
class ActualCut:
	direction: CutDirection
	x1_mm: float
	y1_mm: float
	x2_mm: float
	y2_mm: float
	kerf_width_mm: float


@dataclass(frozen=True)
class SheetCutResult:
	sheet_name: str
	sheet_width_mm: float
	sheet_height_mm: float
	root: CutNode
	placed_parts: list[PlacedPart] = field(default_factory=list)
	waste_areas: list[RectArea] = field(default_factory=list)
	actual_cuts: list[ActualCut] = field(default_factory=list)


@dataclass(frozen=True)
class CuttingResult:
	sheets: list[SheetCutResult] = field(default_factory=list)
	unplaced_parts: list[UnplacedPart] = field(default_factory=list)
