from dataclasses import dataclass
from enum import Enum

from cutting_app.app.domain.return_remnant import ReturnRemnantProfile


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
	new_sheet_count: int
	new_material_area_mm2: float
	return_remnant_profile: ReturnRemnantProfile
	return_remnant_area_mm2: float
	largest_return_remnant_area_mm2: float
	longest_return_remnant_side_mm: float
	longest_return_remnant_area_mm2: float
	largest_compact_square_area_mm2: float
	compact_return_remnant_area_mm2: float
	cut_length_mm: float
	pass_count: int
	strip_turn_count: int
	size_setting_count: int
	technical_order: int

	@property
	def selection_key(self) -> tuple[float | int, ...]:
		return (
			self.unplaced_part_count,
			-self.placed_area_mm2,
			self.new_sheet_count,
			self.new_material_area_mm2,
			*self._return_remnant_selection_key(),
			self.cut_length_mm,
			self.pass_count,
			self.strip_turn_count,
			self.size_setting_count,
			self.technical_order,
		)

	def _return_remnant_selection_key(self) -> tuple[float, ...]:
		if self.return_remnant_profile == ReturnRemnantProfile.LONG:
			return (
				-self.longest_return_remnant_side_mm,
				-self.longest_return_remnant_area_mm2,
				-self.return_remnant_area_mm2,
			)

		if self.return_remnant_profile == ReturnRemnantProfile.COMPACT:
			return (
				-self.largest_compact_square_area_mm2,
				-self.compact_return_remnant_area_mm2,
				-self.return_remnant_area_mm2,
			)

		return (
			-self.return_remnant_area_mm2,
			-self.largest_return_remnant_area_mm2,
		)


@dataclass(frozen=True)
class OptimizationSummary:
	selected_variant_id: str
	evaluated_variant_count: int
	score: OptimizationVariantScore
