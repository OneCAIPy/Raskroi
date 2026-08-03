from dataclasses import dataclass
from enum import Enum

from cutting_app.app.domain.cut_tree import RectArea


class ReturnRemnantProfile(str, Enum):
	MAX_USEFUL_AREA = "max_useful_area"
	LONG = "long"
	COMPACT = "compact"


@dataclass(frozen=True)
class ReturnRemnantSettings:
	min_long_side_mm: float = 400.0
	min_short_side_mm: float = 80.0
	min_area_mm2: float = 40_000.0
	value_profile: ReturnRemnantProfile = ReturnRemnantProfile.MAX_USEFUL_AREA

	def __post_init__(self) -> None:
		try:
			value_profile = ReturnRemnantProfile(self.value_profile)
		except ValueError as error:
			raise ValueError("Неизвестный профиль возвратного остатка.") from error
		object.__setattr__(self, "value_profile", value_profile)

		if self.min_long_side_mm < 0:
			raise ValueError("Минимальная длинная сторона остатка не может быть отрицательной.")
		if self.min_short_side_mm < 0:
			raise ValueError("Минимальная короткая сторона остатка не может быть отрицательной.")
		if self.min_area_mm2 < 0:
			raise ValueError("Минимальная площадь остатка не может быть отрицательной.")
		if self.min_long_side_mm < self.min_short_side_mm:
			raise ValueError(
				"Минимальная длинная сторона остатка не может быть меньше короткой."
			)


@dataclass(frozen=True)
class ReturnRemnant:
	sheet_name: str
	area: RectArea

	@property
	def width_mm(self) -> float:
		return self.area.width_mm

	@property
	def height_mm(self) -> float:
		return self.area.height_mm

	@property
	def long_side_mm(self) -> float:
		return max(self.width_mm, self.height_mm)

	@property
	def short_side_mm(self) -> float:
		return min(self.width_mm, self.height_mm)

	@property
	def area_mm2(self) -> float:
		return self.width_mm * self.height_mm
