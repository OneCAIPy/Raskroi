from dataclasses import dataclass

from cutting_app.app.domain.cut_tree import RectArea


@dataclass(frozen=True)
class ReturnRemnantSettings:
	min_long_side_mm: float = 400.0
	min_short_side_mm: float = 80.0
	min_area_mm2: float = 40_000.0

	def __post_init__(self) -> None:
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
