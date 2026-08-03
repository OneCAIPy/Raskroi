from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.sheet import SheetInput, SheetMargins


def build_basis_agt_3019_parts() -> list[PartInput]:
	return [
		PartInput(
			number=position,
			name=f"Позиция {position}",
			l_mm=l_mm,
			w_mm=w_mm,
			quantity=quantity,
			edges=EdgeSet(
				L1=_basis_edge(),
				L2=_basis_edge(),
				W1=_basis_edge(),
				W2=_basis_edge(),
			),
			rotation_allowed=True,
		)
		for position, l_mm, w_mm, quantity in BASIS_AGT_3019_PARTS
	]


def build_basis_agt_3019_sheets(quantity: int = 20) -> list[SheetInput]:
	return [
		SheetInput(
			name="АГТ 3019",
			width_mm=2800,
			height_mm=1220,
			quantity=quantity,
			margins=SheetMargins(
				left_mm=15,
				top_mm=10,
				right_mm=15,
				bottom_mm=10,
			),
		)
	]


def build_basis_agt_3019_settings() -> CutSettings:
	return CutSettings(kerf_width_mm=4.4)


def _basis_edge() -> EdgeSpec:
	return EdgeSpec(
		thickness_mm=1,
		trimming_allowance_mm=0.5,
		material_name="3019 АГТ Кромка Abs 22*1",
	)


BASIS_AGT_3019_PARTS: tuple[tuple[str, float, float, int], ...] = (
	("1", 401, 801, 2),
	("2", 264, 401, 2),
	("3", 264, 765, 1),
	("4", 258, 759, 1),
	("5", 1314, 768, 1),
	("6", 514, 768, 1),
	("7", 2397, 597, 2),
	("8", 694, 427, 1),
	("9", 694, 432, 2),
	("10", 2000, 97, 1),
	("11", 500, 97, 1),
	("12", 1797, 400, 1),
	("13", 1300, 450, 1),
	("14", 915, 560, 2),
	("15", 2043, 580, 2),
	("16", 360, 516, 2),
	("17", 750, 447, 1),
	("18", 750, 597, 1),
	("19", 750, 100, 1),
	("20", 150, 597, 1),
	("21", 360, 597, 4),
	("22", 750, 200, 1),
	("23", 426, 683, 1),
	("24", 483, 683, 1),
	("25", 972, 347, 2),
	("26", 972, 597, 4),
	("27", 972, 475, 1),
	("28", 483, 697, 1),
	("29", 483, 597, 4),
	("30", 483, 475, 1),
	("31", 1700, 597, 1),
	("32", 2110, 200, 1),
	("33", 1601, 310, 1),
	("34", 362, 289, 2),
	("35", 359, 530, 3),
	("36", 197, 397, 8),
	("37", 754, 468, 2),
	("38", 940, 300, 1),
	("39", 300, 165, 1),
	("40", 2287, 492, 1),
	("41", 2287, 493, 4),
	("42", 2287, 100, 1),
	("43", 2287, 526, 1),
	("44", 597, 492, 1),
	("45", 597, 493, 4),
	("46", 597, 100, 1),
	("47", 597, 526, 1),
	("48", 2297, 492, 4),
	("49", 2297, 100, 1),
	("50", 2297, 200, 1),
	("51", 597, 492, 4),
	("52", 597, 100, 1),
	("53", 597, 200, 1),
)


BASIS_AGT_3019_RETURN_REMNANTS: tuple[tuple[float, float], ...] = (
	(494.6, 99),
	(538.6, 196),
	(596, 184.2),
	(138.2, 1220),
	(529, 122.8),
	(515, 483.2),
	(1382.2, 164),
	(914, 83.2),
	(596, 219.2),
	(596, 219.2),
	(596, 237.2),
	(1600, 92.2),
	(971, 106.2),
	(205.2, 1220),
	(596, 217.2),
	(596, 218.2),
	(280.8, 1220),
)
