from dataclasses import dataclass

from cutting_app.app.domain.cutting_result import CuttingResult
from cutting_app.app.domain.result_issue import ResultIssue
from cutting_app.app.examples.demo_cutting_orders import find_demo_cutting_order
from cutting_app.app.exporters import svg_exporter
from cutting_app.app.services.cutting_result_validator import validate_cutting_result
from cutting_app.app.services.guillotine_optimizer import optimize_guillotine_cutting


@dataclass(frozen=True)
class WebSvgPreview:
	order_slug: str
	order_name: str
	result: CuttingResult
	issues: list[ResultIssue]
	svg: str


def build_sample_svg_preview(order_slug: str = "error") -> WebSvgPreview:
	order = find_demo_cutting_order(order_slug)

	result = optimize_guillotine_cutting(
		parts=order.parts,
		sheets=order.sheets,
		settings=order.settings,
	)
	issues = validate_cutting_result(result)
	svg = svg_exporter.export_cutting_result_to_svg(result, issues=issues)

	return WebSvgPreview(
		order_slug=order.slug,
		order_name=order.name,
		result=result,
		issues=issues,
		svg=svg,
	)
