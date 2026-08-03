from dataclasses import replace

from cutting_app.app.domain.cut_tree import CutNode, RectArea
from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.return_remnant import ReturnRemnant, ReturnRemnantSettings
from cutting_app.app.services.area_metrics_calculator import (
	calculate_material_utilization_with_return_remnants_percent,
)


def collect_return_remnants(
	*,
	root: CutNode,
	sheet_name: str,
	settings: ReturnRemnantSettings,
) -> list[ReturnRemnant]:
	waste_leaf_areas: list[RectArea] = []
	_collect_waste_leaf_areas(root, waste_leaf_areas)

	return [
		ReturnRemnant(sheet_name=sheet_name, area=area)
		for area in sorted(
			waste_leaf_areas,
			key=lambda item: (item.y_mm, item.x_mm, item.width_mm, item.height_mm),
		)
		if meets_return_remnant_thresholds(area, settings)
	]


def meets_return_remnant_thresholds(
	area: RectArea,
	settings: ReturnRemnantSettings,
) -> bool:
	long_side_mm = max(area.width_mm, area.height_mm)
	short_side_mm = min(area.width_mm, area.height_mm)
	area_mm2 = area.width_mm * area.height_mm

	return (
		long_side_mm >= settings.min_long_side_mm
		and short_side_mm >= settings.min_short_side_mm
		and area_mm2 >= settings.min_area_mm2
	)


def attach_return_remnants(
	result: CuttingResult,
	settings: ReturnRemnantSettings,
) -> CuttingResult:
	sheets = []
	return_remnants: list[ReturnRemnant] = []

	for sheet in result.sheets:
		sheet_return_remnants = collect_return_remnants(
			root=sheet.root,
			sheet_name=sheet.sheet_name,
			settings=settings,
		)
		return_remnant_area_mm2 = sum(
			remnant.area_mm2
			for remnant in sheet_return_remnants
		)
		sheets.append(
			replace(
				sheet,
				return_remnants=sheet_return_remnants,
				metrics=replace(
					sheet.metrics,
					return_remnant_count=len(sheet_return_remnants),
					return_remnant_area_mm2=return_remnant_area_mm2,
					material_utilization_with_return_remnants_percent=(
						calculate_material_utilization_with_return_remnants_percent(
							placed_area_mm2=sheet.metrics.placed_area_mm2,
							return_remnant_area_mm2=return_remnant_area_mm2,
							used_material_area_mm2=sheet.metrics.sheet_area_mm2,
						)
					),
				),
			)
		)
		return_remnants.extend(sheet_return_remnants)

	return_remnant_area_mm2 = sum(
		remnant.area_mm2
		for remnant in return_remnants
	)
	return replace(
		result,
		sheets=sheets,
		return_remnants=return_remnants,
		metrics=replace(
			result.metrics,
			return_remnant_count=len(return_remnants),
			return_remnant_area_mm2=return_remnant_area_mm2,
			material_utilization_with_return_remnants_percent=(
				calculate_material_utilization_with_return_remnants_percent(
					placed_area_mm2=result.metrics.placed_area_mm2,
					return_remnant_area_mm2=return_remnant_area_mm2,
					used_material_area_mm2=result.metrics.sheet_area_mm2,
				)
			),
		),
	)


def _collect_waste_leaf_areas(
	node: CutNode,
	areas: list[RectArea],
) -> None:
	if node.is_leaf:
		if node.is_waste:
			areas.append(node.area)
		return

	if node.first is not None:
		_collect_waste_leaf_areas(node.first, areas)
	if node.second is not None:
		_collect_waste_leaf_areas(node.second, areas)
