from dataclasses import dataclass

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.sheet import SheetInput, SheetMargins


@dataclass(frozen=True)
class DemoCuttingOrder:
	name: str
	parts: list[PartInput]
	sheets: list[SheetInput]
	settings: CutSettings


def build_demo_order_with_unplaced_part() -> DemoCuttingOrder:
	return DemoCuttingOrder(
		name="Тестовый раскрой с неразмещённой деталью",
		parts=_build_parts(),
		sheets=_build_sheets(),
		settings=CutSettings(kerf_width_mm=4),
	)


def _build_parts() -> list[PartInput]:
	return [
		PartInput(
			number="A1",
			name="Боковина",
			l_mm=720,
			w_mm=500,
			quantity=2,
			edges=EdgeSet(
				L1=EdgeSpec(thickness_mm=1, trimming_allowance_mm=0.5),
				L2=EdgeSpec(thickness_mm=1, trimming_allowance_mm=0.5),
				W1=EdgeSpec(thickness_mm=2),
			),
			rotation_allowed=True,
		),
		PartInput(
			number="A2",
			name="Полка",
			l_mm=680,
			w_mm=300,
			quantity=3,
			edges=EdgeSet(
				L1=EdgeSpec(thickness_mm=1),
				W1=EdgeSpec(thickness_mm=1),
			),
			rotation_allowed=True,
		),
		PartInput(
			number="ERR",
			name="Слишком большая деталь",
			l_mm=5000,
			w_mm=3000,
			quantity=1,
			edges=EdgeSet(),
			rotation_allowed=False,
		),
	]


def _build_sheets() -> list[SheetInput]:
	return [
		SheetInput(
			name="Остаток 900×1200",
			width_mm=900,
			height_mm=1200,
			quantity=1,
			is_remnant=True,
			margins=SheetMargins(
				left_mm=10,
				top_mm=10,
				right_mm=10,
				bottom_mm=10,
			),
		),
		SheetInput(
			name="Лист ЛДСП 2800×2070",
			width_mm=2800,
			height_mm=2070,
			quantity=1,
			is_remnant=False,
			margins=SheetMargins(
				left_mm=15,
				top_mm=15,
				right_mm=15,
				bottom_mm=15,
			),
		),
	]
