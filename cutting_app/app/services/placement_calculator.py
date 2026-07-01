from dataclasses import dataclass

from cutting_app.app.domain.part import PartSizes
from cutting_app.app.domain.placement import Rotation


@dataclass(frozen=True)
class PlacedDimensions:
	width_mm: float
	height_mm: float


def calculate_placed_dimensions(
	sizes: PartSizes,
	rotation: Rotation,
) -> PlacedDimensions:
	if rotation == Rotation.DEG_90:
		return PlacedDimensions(
			width_mm=sizes.cutting_w_mm,
			height_mm=sizes.cutting_l_mm,
		)

	return PlacedDimensions(
		width_mm=sizes.cutting_l_mm,
		height_mm=sizes.cutting_w_mm,
	)