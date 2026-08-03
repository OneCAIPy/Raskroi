from cutting_app.app.domain.edge import EdgeSet, EdgeSide, EdgeSpec
from cutting_app.app.domain.edge_consumption import EdgeMaterialConsumption
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.edge_consumption_calculator import (
	build_part_edge_segments,
	summarize_edge_segments,
)
from tests.basis_agt_3019_fixture import build_basis_agt_3019_parts


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

	for part in build_basis_agt_3019_parts():
		for copy_index in range(part.quantity):
			segments.extend(
				build_part_edge_segments(
					part=part,
					part_number=f"{part.number}-{copy_index + 1}",
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
