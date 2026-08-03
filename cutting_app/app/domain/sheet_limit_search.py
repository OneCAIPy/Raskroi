from dataclasses import dataclass
from enum import Enum

from cutting_app.app.domain.cutting_result import CuttingResult


class SheetLimitSearchStatus(str, Enum):
	FOUND = "found"
	PROVEN_IMPOSSIBLE_BY_AREA = "proven_impossible_by_area"
	NOT_FOUND_WITHIN_BUDGET = "not_found_within_budget"


@dataclass(frozen=True)
class SheetLimitSearchSettings:
	sheet_limit: int
	beam_width: int = 64
	branch_factor: int = 6
	max_variants: int = 24

	def __post_init__(self) -> None:
		if self.sheet_limit <= 0:
			raise ValueError("Лимит листов должен быть положительным.")
		if self.beam_width <= 0:
			raise ValueError("Ширина поиска должна быть положительной.")
		if self.branch_factor <= 0:
			raise ValueError("Коэффициент ветвления должен быть положительным.")
		if self.max_variants <= 0:
			raise ValueError("Количество вариантов должно быть положительным.")


@dataclass(frozen=True)
class SheetLimitSearchReport:
	status: SheetLimitSearchStatus
	settings: SheetLimitSearchSettings
	evaluated_variant_count: int
	evaluated_state_count: int
	pruned_state_count: int
	best_placed_part_count: int
	best_placed_area_mm2: float
	deepest_search_prefix_part_count: int
	deepest_search_prefix_area_mm2: float
	result: CuttingResult | None = None
	best_partial_result: CuttingResult | None = None

	@property
	def found(self) -> bool:
		return self.status == SheetLimitSearchStatus.FOUND

	@property
	def is_proven_impossible(self) -> bool:
		return self.status == SheetLimitSearchStatus.PROVEN_IMPOSSIBLE_BY_AREA
