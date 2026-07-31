from cutting_app.app.domain.edge import EdgeSet, EdgeSide, EdgeSpec
from cutting_app.app.domain.edge_consumption import EdgeMaterialConsumption
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.edge_consumption_calculator import (
	build_part_edge_segments,
	summarize_edge_segments,
)


def test_edge_consumption_uses_logical_final_sizes_and_adds_overhang_once() -> None:
	part = PartInput(
		number="A1",
		name="Фасад",
		l_mm=300,
		w_mm=800,
		quantity=1,
		edges=EdgeSet(
			L1=EdgeSpec(
				thickness_mm=1,
				tape_overhang_mm=10,
				material_name="ABS белая",
			),
			L2=EdgeSpec(thickness_mm=1, material_name="ABS белая"),
			W1=EdgeSpec(
				thickness_mm=2,
				tape_overhang_mm=20,
				material_name="ABS графит",
			),
			W2=EdgeSpec(
				thickness_mm=1,
				tape_overhang_mm=5,
				material_name="ABS белая",
			),
		),
	)

	segments = build_part_edge_segments(part=part, part_number="A1-1")
	consumption = summarize_edge_segments(segments)

	assert [segment.side for segment in segments] == [EdgeSide.L1, EdgeSide.L2, EdgeSide.W1, EdgeSide.W2]
	assert [segment.base_length_mm for segment in segments] == [300, 300, 800, 800]
	assert [segment.total_length_mm for segment in segments] == [310, 300, 820, 805]
	assert consumption.segment_count == 4
	assert consumption.base_length_mm == 2200
	assert consumption.overhang_length_mm == 35
	assert consumption.total_length_mm == 2235
	assert consumption.by_material == (
		EdgeMaterialConsumption(
			material_name="ABS белая",
			thickness_mm=1,
			segment_count=3,
			base_length_mm=1400,
			overhang_length_mm=15,
			total_length_mm=1415,
		),
		EdgeMaterialConsumption(
			material_name="ABS графит",
			thickness_mm=2,
			segment_count=1,
			base_length_mm=800,
			overhang_length_mm=20,
			total_length_mm=820,
		),
	)


def test_part_without_edges_has_empty_consumption() -> None:
	part = PartInput(
		number="A1",
		name="Полка",
		l_mm=300,
		w_mm=800,
		quantity=1,
		edges=EdgeSet(),
	)

	consumption = summarize_edge_segments(
		build_part_edge_segments(part=part, part_number="A1")
	)

	assert consumption.segment_count == 0
	assert consumption.base_length_mm == 0
	assert consumption.overhang_length_mm == 0
	assert consumption.total_length_mm == 0
	assert consumption.segments == ()
	assert consumption.by_material == ()


def test_basis_reference_order_has_261526_mm_and_372_edge_segments() -> None:
	segments = []

	for position, l_mm, w_mm, quantity in _basis_reference_parts():
		part = PartInput(
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
		)

		for copy_index in range(quantity):
			segments.extend(
				build_part_edge_segments(
					part=part,
					part_number=f"{position}-{copy_index + 1}",
				)
			)

	consumption = summarize_edge_segments(segments)

	assert consumption.segment_count == 372
	assert consumption.base_length_mm == 261526
	assert consumption.overhang_length_mm == 0
	assert consumption.total_length_mm == 261526
	assert consumption.by_material == (
		EdgeMaterialConsumption(
			material_name="3019 АГТ Кромка Abs 22*1",
			thickness_mm=1,
			segment_count=372,
			base_length_mm=261526,
			overhang_length_mm=0,
			total_length_mm=261526,
		),
	)


def _basis_edge() -> EdgeSpec:
	return EdgeSpec(
		thickness_mm=1,
		trimming_allowance_mm=0.5,
		material_name="3019 АГТ Кромка Abs 22*1",
	)


def _basis_reference_parts() -> tuple[tuple[str, float, float, int], ...]:
	return (
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
