from dataclasses import dataclass

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.edge import EdgeSet, EdgeSpec
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.result_issue import ResultIssue
from cutting_app.app.domain.sheet import SheetInput, SheetMargins
from cutting_app.app.exporters import svg_exporter
from cutting_app.app.services.cutting_result_validator import validate_cutting_result
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting


@dataclass(frozen=True)
class WebSvgPreview:
	result: CuttingResult
	issues: list[ResultIssue]
	svg: str


def build_sample_svg_preview() -> WebSvgPreview:
	result = optimize_guillotine_cutting(
		parts=_sample_parts(),
		sheets=_sample_sheets(),
		settings=CutSettings(kerf_width_mm=4),
	)
	issues = validate_cutting_result(result)
	svg = svg_exporter.export_cutting_result_to_svg(result, issues=issues)

	return WebSvgPreview(
		result=result,
		issues=issues,
		svg=svg,
	)


def _sample_parts() -> list[PartInput]:
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


def _sample_sheets() -> list[SheetInput]:
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