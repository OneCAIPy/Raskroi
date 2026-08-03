from dataclasses import dataclass, field

from cutting_app.app.domain.cut_tree import CutDirection, CutNode, RectArea
from cutting_app.app.domain.edge import EdgeSet
from cutting_app.app.domain.edge_consumption import EdgeConsumption
from cutting_app.app.domain.optimization import OptimizationSummary
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.domain.production_cut_plan import ProductionCutPlan
from cutting_app.app.domain.return_remnant import ReturnRemnant


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
	edges: EdgeSet = field(default_factory=EdgeSet)


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
class SheetCutMetrics:
	sheet_area_mm2: float = 0
	usable_area_mm2: float = 0
	placed_area_mm2: float = 0
	waste_area_mm2: float = 0
	kerf_area_mm2: float = 0
	material_utilization_percent: float = 0
	working_area_efficiency_percent: float = 0
	return_remnant_count: int = 0
	return_remnant_area_mm2: float = 0
	material_utilization_with_return_remnants_percent: float = 0


@dataclass(frozen=True)
class CuttingMetrics:
	sheet_count: int = 0
	placed_part_count: int = 0
	unplaced_part_count: int = 0
	sheet_area_mm2: float = 0
	usable_area_mm2: float = 0
	placed_area_mm2: float = 0
	waste_area_mm2: float = 0
	kerf_area_mm2: float = 0
	material_utilization_percent: float = 0
	working_area_efficiency_percent: float = 0
	return_remnant_count: int = 0
	return_remnant_area_mm2: float = 0
	material_utilization_with_return_remnants_percent: float = 0


@dataclass(frozen=True)
class SheetCutResult:
	sheet_name: str
	sheet_width_mm: float
	sheet_height_mm: float
	root: CutNode
	sheet_stock_name: str = ""
	sheet_is_remnant: bool = False
	placed_parts: list[PlacedPart] = field(default_factory=list)
	waste_areas: list[RectArea] = field(default_factory=list)
	actual_cuts: list[ActualCut] = field(default_factory=list)
	metrics: SheetCutMetrics = field(default_factory=SheetCutMetrics)
	production_cut_plan: ProductionCutPlan | None = None
	edge_consumption: EdgeConsumption = field(default_factory=EdgeConsumption)
	return_remnants: list[ReturnRemnant] = field(default_factory=list)


@dataclass(frozen=True)
class CuttingResult:
	sheets: list[SheetCutResult] = field(default_factory=list)
	unplaced_parts: list[UnplacedPart] = field(default_factory=list)
	metrics: CuttingMetrics = field(default_factory=CuttingMetrics)
	edge_consumption: EdgeConsumption = field(default_factory=EdgeConsumption)
	optimization: OptimizationSummary | None = None
	return_remnants: list[ReturnRemnant] = field(default_factory=list)
