from collections.abc import Iterable

from cutting_app.app.domain.cutting_result import (
	CuttingMetrics,
	CuttingResult,
	SheetCutResult,
	UnplacedPart,
)
from cutting_app.app.services.area_metrics_calculator import (
	calculate_material_utilization_percent,
	calculate_working_area_efficiency_percent,
)
from cutting_app.app.services.edge_consumption_calculator import (
	summarize_edge_segments,
)


def assemble_cutting_result(
	sheets: Iterable[SheetCutResult],
	unplaced_parts: Iterable[UnplacedPart] = (),
) -> CuttingResult:
	sheet_list = list(sheets)
	unplaced_part_list = list(unplaced_parts)
	sheet_area_mm2 = sum(sheet.metrics.sheet_area_mm2 for sheet in sheet_list)
	usable_area_mm2 = sum(sheet.metrics.usable_area_mm2 for sheet in sheet_list)
	placed_area_mm2 = sum(sheet.metrics.placed_area_mm2 for sheet in sheet_list)
	waste_area_mm2 = sum(sheet.metrics.waste_area_mm2 for sheet in sheet_list)
	kerf_area_mm2 = sum(sheet.metrics.kerf_area_mm2 for sheet in sheet_list)

	return CuttingResult(
		sheets=sheet_list,
		unplaced_parts=unplaced_part_list,
		metrics=CuttingMetrics(
			sheet_count=len(sheet_list),
			placed_part_count=sum(len(sheet.placed_parts) for sheet in sheet_list),
			unplaced_part_count=len(unplaced_part_list),
			sheet_area_mm2=sheet_area_mm2,
			usable_area_mm2=usable_area_mm2,
			placed_area_mm2=placed_area_mm2,
			waste_area_mm2=waste_area_mm2,
			kerf_area_mm2=kerf_area_mm2,
			material_utilization_percent=calculate_material_utilization_percent(
				placed_area_mm2=placed_area_mm2,
				used_material_area_mm2=sheet_area_mm2,
			),
			working_area_efficiency_percent=(
				calculate_working_area_efficiency_percent(
					placed_area_mm2=placed_area_mm2,
					working_area_mm2=usable_area_mm2,
				)
			),
		),
		edge_consumption=summarize_edge_segments(
			segment
			for sheet in sheet_list
			for segment in sheet.edge_consumption.segments
		),
	)
