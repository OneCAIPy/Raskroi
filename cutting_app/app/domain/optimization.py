from dataclasses import dataclass
from enum import Enum


class PartOrdering(str, Enum):
	AREA_DESC = "area_desc"
	LONG_SIDE_DESC = "long_side_desc"
	SHORT_SIDE_DESC = "short_side_desc"


class PlacementHeuristic(str, Enum):
	BEST_AREA_FIT = "best_area_fit"
	BEST_SHORT_SIDE_FIT = "best_short_side_fit"


class SheetSelectionHeuristic(str, Enum):
	FIRST_FIT = "first_fit"
	BEST_USED_SHEET_FIT = "best_used_sheet_fit"


class SplitHeuristic(str, Enum):
	MIN_KERF_LOSS = "min_kerf_loss"
	SHORTER_LEFTOVER_AXIS = "shorter_leftover_axis"


class RotationPreference(str, Enum):
	UNROTATED_FIRST = "unrotated_first"
	ROTATED_FIRST = "rotated_first"


@dataclass(frozen=True)
class OptimizationVariant:
	variant_id: str
	technical_order: int
	part_ordering: PartOrdering
	placement_heuristic: PlacementHeuristic
	split_heuristic: SplitHeuristic
	rotation_preference: RotationPreference
	sheet_selection_heuristic: SheetSelectionHeuristic = SheetSelectionHeuristic.FIRST_FIT


@dataclass(frozen=True)
class OptimizationVariantScore:
	unplaced_part_count: int
	placed_area_mm2: float
	sheet_count: int
	material_utilization_percent: float
	cut_length_mm: float
	pass_count: int
	strip_turn_count: int
	size_setting_count: int
	technical_order: int

	@property
	def selection_key(self) -> tuple[int, float, int, float, float, int, int, int, int]:
		return (
			self.unplaced_part_count,
			-self.placed_area_mm2,
			self.sheet_count,
			-self.material_utilization_percent,
			self.cut_length_mm,
			self.pass_count,
			self.strip_turn_count,
			self.size_setting_count,
			self.technical_order,
		)


@dataclass(frozen=True)
class OptimizationSummary:
	selected_variant_id: str
	evaluated_variant_count: int
	score: OptimizationVariantScore
