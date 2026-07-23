from dataclasses import dataclass
from enum import Enum

from cutting_app.app.domain.cut_tree import CutDirection, RectArea


class SawPassType(str, Enum):
	START_TRIM = "start_trim"
	SPLIT = "split"
	END_TRIM = "end_trim"


@dataclass(frozen=True)
class CuttingCycleOutput:
	output_id: str
	area: RectArea


@dataclass(frozen=True)
class SawPass:
	cycle_id: str
	sequence_number: int
	pass_type: SawPassType
	direction: CutDirection
	x1_mm: float
	y1_mm: float
	x2_mm: float
	y2_mm: float
	nominal_kerf_width_mm: float
	actual_removed_width_mm: float
	after_output_id: str | None = None

	@property
	def length_mm(self) -> float:
		if self.direction == CutDirection.VERTICAL:
			return abs(self.y2_mm - self.y1_mm)

		return abs(self.x2_mm - self.x1_mm)

	@property
	def nominal_cut_area_mm2(self) -> float:
		return self.length_mm * self.nominal_kerf_width_mm

	@property
	def actual_removed_area_mm2(self) -> float:
		return self.length_mm * self.actual_removed_width_mm


@dataclass(frozen=True)
class CuttingCycleMetrics:
	pass_count: int
	cut_length_mm: float
	nominal_cut_area_mm2: float
	actual_removed_area_mm2: float


@dataclass(frozen=True)
class CuttingCycle:
	cycle_id: str
	source_area: RectArea
	direction: CutDirection
	outputs: tuple[CuttingCycleOutput, ...]
	saw_passes: tuple[SawPass, ...]
	metrics: CuttingCycleMetrics
