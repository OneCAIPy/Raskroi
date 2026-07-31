from collections.abc import Iterable

from cutting_app.app.domain.edge import EdgeSide
from cutting_app.app.domain.edge_consumption import (
	EdgeConsumption,
	EdgeMaterialConsumption,
	EdgeSegment,
)
from cutting_app.app.domain.part import PartInput
from cutting_app.app.services.edge_calculator import calculate_edge_side_length_mm


def build_part_edge_segments(
	part: PartInput,
	part_number: str,
) -> tuple[EdgeSegment, ...]:
	segments: list[EdgeSegment] = []

	for side in EdgeSide:
		edge = part.edges.by_side(side)
		if not edge.has_edge:
			continue

		segments.append(
			EdgeSegment(
				part_number=part_number,
				source_part_number=part.number,
				part_name=part.name,
				side=side,
				material_name=edge.material_name,
				thickness_mm=edge.thickness_mm,
				base_length_mm=calculate_edge_side_length_mm(part, side),
				tape_overhang_mm=edge.tape_overhang_mm,
			)
		)

	return tuple(segments)


def summarize_edge_segments(
	segments: Iterable[EdgeSegment],
) -> EdgeConsumption:
	segment_tuple = tuple(segments)
	grouped: dict[tuple[str, float], list[EdgeSegment]] = {}

	for segment in segment_tuple:
		key = (segment.material_name, segment.thickness_mm)
		grouped.setdefault(key, []).append(segment)

	by_material = tuple(
		_summarize_material(material_name, thickness_mm, material_segments)
		for (material_name, thickness_mm), material_segments in sorted(grouped.items())
	)

	return EdgeConsumption(
		segments=segment_tuple,
		by_material=by_material,
		segment_count=len(segment_tuple),
		base_length_mm=sum(segment.base_length_mm for segment in segment_tuple),
		overhang_length_mm=sum(segment.tape_overhang_mm for segment in segment_tuple),
		total_length_mm=sum(segment.total_length_mm for segment in segment_tuple),
	)


def _summarize_material(
	material_name: str,
	thickness_mm: float,
	segments: list[EdgeSegment],
) -> EdgeMaterialConsumption:
	base_length_mm = sum(segment.base_length_mm for segment in segments)
	overhang_length_mm = sum(segment.tape_overhang_mm for segment in segments)

	return EdgeMaterialConsumption(
		material_name=material_name,
		thickness_mm=thickness_mm,
		segment_count=len(segments),
		base_length_mm=base_length_mm,
		overhang_length_mm=overhang_length_mm,
		total_length_mm=base_length_mm + overhang_length_mm,
	)
