from dataclasses import dataclass

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.sheet import SheetInput, SheetMargins


@dataclass(frozen=True)
class DemoCuttingOrder:
	slug: str
	name: str
	parts: list[PartInput]
	sheets: list[SheetInput]
	settings: CutSettings


def list_demo_cutting_orders() -> list[DemoCuttingOrder]:
	return [
		build_demo_order_simple_without_errors(),
		build_demo_order_with_remnant(),
		build_demo_order_with_rotation_and_edges(),
		build_demo_order_realistic_cabinet(),
		build_demo_order_with_unplaced_part(),
	]


def find_demo_cutting_order(slug: str) -> DemoCuttingOrder:
	for order in list_demo_cutting_orders():
		if order.slug == slug:
			return order

	raise ValueError(f"Unknown demo cutting order slug: {slug}")


def build_demo_order_simple_without_errors() -> DemoCuttingOrder:
	return DemoCuttingOrder(
		slug="simple",
		name="Простой раскрой без ошибок",
		parts=[
			PartInput(
				number="S1",
				name="Большая полка",
				l_mm=500,
				w_mm=300,
				quantity=1,
				edges=EdgeSet(),
				rotation_allowed=True,
			),
			PartInput(
				number="S2",
				name="Малая полка",
				l_mm=250,
				w_mm=250,
				quantity=2,
				edges=EdgeSet(),
				rotation_allowed=True,
			),
		],
		sheets=[
			SheetInput(
				name="Тестовый лист 1000×700",
				width_mm=1000,
				height_mm=700,
				quantity=1,
				is_remnant=False,
				margins=_margins(10),
			),
		],
		settings=_default_settings(),
	)


def build_demo_order_with_remnant() -> DemoCuttingOrder:
	return DemoCuttingOrder(
		slug="remnant",
		name="Раскрой с приоритетом остатка",
		parts=[
			PartInput(
				number="R1",
				name="Деталь из остатка 1",
				l_mm=500,
				w_mm=300,
				quantity=2,
				edges=EdgeSet(L1=_edge_1mm()),
				rotation_allowed=True,
			),
			PartInput(
				number="R2",
				name="Деталь из остатка 2",
				l_mm=450,
				w_mm=250,
				quantity=2,
				edges=EdgeSet(W1=_edge_1mm()),
				rotation_allowed=True,
			),
		],
		sheets=[
			SheetInput(
				name="Остаток 900×1200",
				width_mm=900,
				height_mm=1200,
				quantity=1,
				is_remnant=True,
				margins=_margins(10),
			),
			SheetInput(
				name="Лист ЛДСП 2800×2070",
				width_mm=2800,
				height_mm=2070,
				quantity=1,
				is_remnant=False,
				margins=_margins(15),
			),
		],
		settings=_default_settings(),
	)


def build_demo_order_with_rotation_and_edges() -> DemoCuttingOrder:
	return DemoCuttingOrder(
		slug="rotation",
		name="Раскрой с поворотом и кромкой",
		parts=[
			PartInput(
				number="ROT1",
				name="Длинная деталь, помещается только с поворотом",
				l_mm=1100,
				w_mm=350,
				quantity=1,
				edges=EdgeSet(
					L1=_edge_1mm(),
					L2=_edge_1mm(),
					W1=EdgeSpec(thickness_mm=2),
				),
				rotation_allowed=True,
			),
		],
		sheets=[
			SheetInput(
				name="Узкий лист 600×1200",
				width_mm=600,
				height_mm=1200,
				quantity=1,
				is_remnant=False,
				margins=_margins(10),
			),
		],
		settings=_default_settings(),
	)


def build_demo_order_realistic_cabinet() -> DemoCuttingOrder:
	return DemoCuttingOrder(
		slug="cabinet",
		name="Почти реальный корпусный заказ",
		parts=[
			PartInput(
				number="K1",
				name="Боковина",
				l_mm=720,
				w_mm=500,
				quantity=2,
				edges=EdgeSet(L1=_edge_1mm(), L2=_edge_1mm()),
				rotation_allowed=True,
			),
			PartInput(
				number="K2",
				name="Дно/крыша",
				l_mm=680,
				w_mm=500,
				quantity=2,
				edges=EdgeSet(L1=_edge_1mm()),
				rotation_allowed=True,
			),
			PartInput(
				number="K3",
				name="Полка",
				l_mm=680,
				w_mm=300,
				quantity=3,
				edges=EdgeSet(L1=_edge_1mm()),
				rotation_allowed=True,
			),
			PartInput(
				number="K4",
				name="Цоколь",
				l_mm=680,
				w_mm=100,
				quantity=2,
				edges=EdgeSet(L1=_edge_1mm()),
				rotation_allowed=True,
			),
			PartInput(
				number="K5",
				name="Фальш-панель",
				l_mm=716,
				w_mm=396,
				quantity=2,
				edges=EdgeSet(
					L1=_edge_1mm(),
					L2=_edge_1mm(),
					W1=_edge_1mm(),
					W2=_edge_1mm(),
				),
				rotation_allowed=True,
			),
		],
		sheets=[
			SheetInput(
				name="Лист ЛДСП 2800×2070",
				width_mm=2800,
				height_mm=2070,
				quantity=1,
				is_remnant=False,
				margins=_margins(15),
			),
		],
		settings=_default_settings(),
	)


def build_demo_order_with_unplaced_part() -> DemoCuttingOrder:
	return DemoCuttingOrder(
		slug="error",
		name="Тестовый раскрой с неразмещённой деталью",
		parts=[
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
					L1=_edge_1mm(),
					W1=_edge_1mm(),
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
		],
		sheets=[
			SheetInput(
				name="Остаток 900×1200",
				width_mm=900,
				height_mm=1200,
				quantity=1,
				is_remnant=True,
				margins=_margins(10),
			),
			SheetInput(
				name="Лист ЛДСП 2800×2070",
				width_mm=2800,
				height_mm=2070,
				quantity=1,
				is_remnant=False,
				margins=_margins(15),
			),
		],
		settings=_default_settings(),
	)


def _default_settings() -> CutSettings:
	return CutSettings(kerf_width_mm=4)


def _edge_1mm() -> EdgeSpec:
	return EdgeSpec(thickness_mm=1)


def _margins(value_mm: float) -> SheetMargins:
	return SheetMargins(
		left_mm=value_mm,
		top_mm=value_mm,
		right_mm=value_mm,
		bottom_mm=value_mm,
	)
