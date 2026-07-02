from collections import defaultdict
from dataclasses import dataclass
from xml.sax.saxutils import escape, quoteattr

from cutting_app.app.domain.cut_tree import RectArea
from cutting_app.app.domain.cutting_result import (
	ActualCut,
	CuttingResult,
	PlacedPart,
	SheetCutResult,
	UnplacedPart,
)
from cutting_app.app.domain.edge import EdgeSide, EdgeSpec
from cutting_app.app.domain.placement import VisualSide
from cutting_app.app.domain.result_issue import ResultIssue
from cutting_app.app.services.edge_visual_mapper import map_edge_side_to_visual_side


@dataclass(frozen=True)
class SvgExportConfig:
	scale_px_per_mm: float = 0.2
	page_margin_px: float = 24
	sheet_gap_px: float = 64
	title_height_px: float = 28
	message_line_height_px: float = 18
	min_page_width_px: float = 720
	part_label_min_width_px: float = 42
	part_label_min_height_px: float = 28
	edge_stroke_width_px: float = 4
	cut_min_stroke_width_px: float = 1.5


def export_cutting_result_to_svg(
	result: CuttingResult,
	issues: list[ResultIssue] | None = None,
	config: SvgExportConfig = SvgExportConfig(),
) -> str:
	issue_list = list(issues or [])
	layout = _make_layout(result, issue_list, config)
	parts = [
		'<?xml version="1.0" encoding="UTF-8"?>',
		(
			'<svg xmlns="http://www.w3.org/2000/svg" '
			f'width="{_fmt(layout.width_px)}" height="{_fmt(layout.height_px)}" '
			f'viewBox="0 0 {_fmt(layout.width_px)} {_fmt(layout.height_px)}" '
			'role="img" aria-label="Карта раскроя">'
		),
		_style_block(),
	]

	if not result.sheets:
		parts.append(_text("Карта раскроя пуста", config.page_margin_px, config.page_margin_px, "empty-title"))

	y_px = config.page_margin_px
	issues_by_sheet = _group_issues_by_sheet(issue_list)
	for sheet in result.sheets:
		parts.append(_draw_sheet(sheet, issues_by_sheet[sheet.sheet_name], config, y_px))
		y_px += _sheet_panel_height(sheet, len(issues_by_sheet[sheet.sheet_name]), config)

	global_issues = [issue for issue in issue_list if issue.sheet_name is None]
	if global_issues or result.unplaced_parts:
		parts.append(_draw_global_messages(result.unplaced_parts, global_issues, config, y_px))

	parts.append("</svg>")
	return "\n".join(parts)


@dataclass(frozen=True)
class _Layout:
	width_px: float
	height_px: float


def _make_layout(
	result: CuttingResult,
	issues: list[ResultIssue],
	config: SvgExportConfig,
) -> _Layout:
	map_width_px = max((sheet.sheet_width_mm * config.scale_px_per_mm for sheet in result.sheets), default=0)
	width_px = max(config.min_page_width_px, map_width_px + config.page_margin_px * 2)

	issues_by_sheet = _group_issues_by_sheet(issues)
	height_px = config.page_margin_px
	for sheet in result.sheets:
		height_px += _sheet_panel_height(sheet, len(issues_by_sheet[sheet.sheet_name]), config)

	global_count = len([issue for issue in issues if issue.sheet_name is None]) + len(result.unplaced_parts)
	if global_count:
		height_px += config.title_height_px + global_count * config.message_line_height_px + config.sheet_gap_px
	if not result.sheets:
		height_px += config.title_height_px
	return _Layout(width_px=width_px, height_px=height_px + config.page_margin_px)


def _sheet_panel_height(sheet: SheetCutResult, issue_count: int, config: SvgExportConfig) -> float:
	message_height_px = issue_count * config.message_line_height_px
	return (
		config.title_height_px
		+ sheet.sheet_height_mm * config.scale_px_per_mm
		+ message_height_px
		+ config.sheet_gap_px
	)


def _draw_sheet(
	sheet: SheetCutResult,
	issues: list[ResultIssue],
	config: SvgExportConfig,
	y_px: float,
) -> str:
	origin_x = config.page_margin_px
	map_y = y_px + config.title_height_px
	parts = [
		_tag("g", {"class": "sheet-panel", "data-sheet-name": sheet.sheet_name}),
		_text(
			f"Лист: {sheet.sheet_name} ({_fmt(sheet.sheet_width_mm)}×{_fmt(sheet.sheet_height_mm)} мм)",
			origin_x,
			y_px + 18,
			"sheet-title",
		),
		_draw_rect(
			0,
			0,
			sheet.sheet_width_mm,
			sheet.sheet_height_mm,
			origin_x,
			map_y,
			config,
			"sheet-outline",
			{"data-kind": "sheet-outline"},
		),
		_draw_area(sheet.root.area, origin_x, map_y, config, "usable-area", {"data-kind": "usable-area"}),
	]

	for waste_area in sheet.waste_areas:
		parts.append(_draw_area(waste_area, origin_x, map_y, config, "waste-area", {"data-kind": "waste-area"}))
	for placed_part in sheet.placed_parts:
		parts.append(_draw_placed_part(placed_part, origin_x, map_y, config))
	for actual_cut in sheet.actual_cuts:
		parts.append(_draw_actual_cut(actual_cut, origin_x, map_y, config))

	message_y = map_y + sheet.sheet_height_mm * config.scale_px_per_mm + config.message_line_height_px
	for issue in issues:
		parts.append(_draw_issue(issue, origin_x, message_y))
		message_y += config.message_line_height_px

	parts.append("</g>")
	return "\n".join(parts)


def _draw_placed_part(part: PlacedPart, origin_x: float, origin_y: float, config: SvgExportConfig) -> str:
	x = origin_x + part.x_mm * config.scale_px_per_mm
	y = origin_y + part.y_mm * config.scale_px_per_mm
	width = part.width_mm * config.scale_px_per_mm
	height = part.height_mm * config.scale_px_per_mm
	parts = [
		_tag(
			"g",
			{
				"class": "placed-part",
				"data-kind": "placed-part",
				"data-part-number": part.part_number,
				"data-source-part-number": part.source_part_number,
				"data-rotation": part.rotation.value,
			},
		),
		f"<title>{escape(part.part_name)}: {_fmt(part.width_mm)}×{_fmt(part.height_mm)} мм</title>",
		_rect_px(x, y, width, height, "part-rect", {"data-kind": "part-rect"}),
	]

	for edge_side in EdgeSide:
		edge = part.edges.by_side(edge_side)
		if edge.has_edge:
			visual_side = map_edge_side_to_visual_side(edge_side, part.rotation)
			parts.append(_draw_edge(part, edge_side, edge, visual_side, origin_x, origin_y, config))

	parts.append(_draw_part_label(part, x, y, width, height, config))
	parts.append("</g>")
	return "\n".join(parts)


def _draw_part_label(part: PlacedPart, x: float, y: float, width: float, height: float, config: SvgExportConfig) -> str:
	center_x = x + width / 2
	center_y = y + height / 2
	if width < config.part_label_min_width_px or height < config.part_label_min_height_px:
		return _text(part.part_number, center_x, center_y, "part-label compact", {"text-anchor": "middle"})
	return (
		f'<text class="part-label" x="{_fmt(center_x)}" y="{_fmt(center_y)}" text-anchor="middle">'
		f'<tspan x="{_fmt(center_x)}" dy="-0.35em">{escape(part.part_number)}</tspan>'
		f'<tspan x="{_fmt(center_x)}" dy="1.2em">{_fmt(part.width_mm)}×{_fmt(part.height_mm)}</tspan>'
		"</text>"
	)


def _draw_edge(
	part: PlacedPart,
	edge_side: EdgeSide,
	edge: EdgeSpec,
	visual_side: VisualSide,
	origin_x: float,
	origin_y: float,
	config: SvgExportConfig,
) -> str:
	x = origin_x + part.x_mm * config.scale_px_per_mm
	y = origin_y + part.y_mm * config.scale_px_per_mm
	width = part.width_mm * config.scale_px_per_mm
	height = part.height_mm * config.scale_px_per_mm
	x1, y1, x2, y2 = _edge_points(x, y, width, height, visual_side)
	return _line_px(
		x1,
		y1,
		x2,
		y2,
		f"edge edge-{edge_side.value.lower()} side-{visual_side.value}",
		{
			"data-kind": "edge",
			"data-logical-side": edge_side.value,
			"data-visual-side": visual_side.value,
			"data-thickness-mm": edge.thickness_mm,
			"data-trimming-allowance-mm": edge.trimming_allowance_mm,
			"data-tape-overhang-mm": edge.tape_overhang_mm,
			"stroke-width": config.edge_stroke_width_px,
		},
	)


def _edge_points(x: float, y: float, width: float, height: float, side: VisualSide) -> tuple[float, float, float, float]:
	if side == VisualSide.TOP:
		return x, y, x + width, y
	if side == VisualSide.RIGHT:
		return x + width, y, x + width, y + height
	if side == VisualSide.BOTTOM:
		return x, y + height, x + width, y + height
	return x, y, x, y + height


def _draw_actual_cut(cut: ActualCut, origin_x: float, origin_y: float, config: SvgExportConfig) -> str:
	stroke_width = max(config.cut_min_stroke_width_px, cut.kerf_width_mm * config.scale_px_per_mm)
	return _line_px(
		origin_x + cut.x1_mm * config.scale_px_per_mm,
		origin_y + cut.y1_mm * config.scale_px_per_mm,
		origin_x + cut.x2_mm * config.scale_px_per_mm,
		origin_y + cut.y2_mm * config.scale_px_per_mm,
		f"actual-cut actual-cut-{cut.direction.value}",
		{"data-kind": "actual-cut", "data-kerf-width-mm": cut.kerf_width_mm, "stroke-width": stroke_width},
	)


def _draw_global_messages(
	unplaced_parts: list[UnplacedPart],
	issues: list[ResultIssue],
	config: SvgExportConfig,
	y_px: float,
) -> str:
	x = config.page_margin_px
	message_y = y_px + 18
	parts = [_tag("g", {"class": "global-messages"}), _text("Ошибки и предупреждения", x, message_y, "sheet-title")]
	message_y += config.message_line_height_px
	for issue in issues:
		parts.append(_draw_issue(issue, x, message_y))
		message_y += config.message_line_height_px
	for part in unplaced_parts:
		parts.append(_text(f"[ERROR] {part.reason_code}: {part.part_number} — {part.reason}", x, message_y, "issue error"))
		message_y += config.message_line_height_px
	parts.append("</g>")
	return "\n".join(parts)


def _draw_issue(issue: ResultIssue, x: float, y: float) -> str:
	text = f"[{issue.level.value.upper()}] {issue.code}: {issue.message}"
	class_name = f"issue {issue.level.value}"
	attrs = {"data-kind": "result-issue", "data-code": issue.code, "data-level": issue.level.value}
	if issue.part_number is not None:
		attrs["data-part-number"] = issue.part_number
	return _text(text, x, y, class_name, attrs)


def _group_issues_by_sheet(issues: list[ResultIssue]) -> defaultdict[str, list[ResultIssue]]:
	grouped: defaultdict[str, list[ResultIssue]] = defaultdict(list)
	for issue in issues:
		if issue.sheet_name is not None:
			grouped[issue.sheet_name].append(issue)
	return grouped


def _draw_area(area: RectArea, origin_x: float, origin_y: float, config: SvgExportConfig, class_name: str, attrs: dict[str, object]) -> str:
	return _draw_rect(area.x_mm, area.y_mm, area.width_mm, area.height_mm, origin_x, origin_y, config, class_name, attrs)


def _draw_rect(
	x_mm: float,
	y_mm: float,
	width_mm: float,
	height_mm: float,
	origin_x: float,
	origin_y: float,
	config: SvgExportConfig,
	class_name: str,
	attrs: dict[str, object],
) -> str:
	return _rect_px(
		origin_x + x_mm * config.scale_px_per_mm,
		origin_y + y_mm * config.scale_px_per_mm,
		width_mm * config.scale_px_per_mm,
		height_mm * config.scale_px_per_mm,
		class_name,
		attrs,
	)


def _rect_px(x: float, y: float, width: float, height: float, class_name: str, attrs: dict[str, object]) -> str:
	return _tag("rect", {"x": x, "y": y, "width": width, "height": height, "class": class_name, **attrs}, closed=True)


def _line_px(x1: float, y1: float, x2: float, y2: float, class_name: str, attrs: dict[str, object]) -> str:
	return _tag("line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "class": class_name, **attrs}, closed=True)


def _text(text: str, x: float, y: float, class_name: str, attrs: dict[str, object] | None = None) -> str:
	return f"<{_tag_name('text', {'x': x, 'y': y, 'class': class_name, **(attrs or {})})}>{escape(text)}</text>"


def _tag(name: str, attrs: dict[str, object], closed: bool = False) -> str:
	return f"<{_tag_name(name, attrs)}{' /' if closed else ''}>"


def _tag_name(name: str, attrs: dict[str, object]) -> str:
	return f"{name} " + " ".join(f"{key}={quoteattr(_fmt(value))}" for key, value in attrs.items())


def _fmt(value: object) -> str:
	if isinstance(value, float):
		return f"{value:.3f}".rstrip("0").rstrip(".")
	return str(value)


def _style_block() -> str:
	return """<defs>
<style>
.sheet-title { font: 600 16px Arial, sans-serif; fill: #222; }
.sheet-outline { fill: #fff; stroke: #222; stroke-width: 1.5; }
.usable-area { fill: #f7fbff; stroke: #4a90e2; stroke-width: 1; stroke-dasharray: 6 4; }
.waste-area { fill: #f3f3f3; stroke: #b8b8b8; stroke-width: 0.8; stroke-dasharray: 3 3; }
.part-rect { fill: #fff7dd; stroke: #333; stroke-width: 1; }
.part-label { font: 12px Arial, sans-serif; fill: #111; pointer-events: none; }
.part-label.compact { font-size: 10px; dominant-baseline: middle; }
.edge { stroke: #d02b2b; stroke-linecap: square; pointer-events: none; }
.actual-cut { stroke: #111; stroke-dasharray: 5 4; pointer-events: none; }
.issue { font: 13px Arial, sans-serif; }
.issue.error { fill: #b00020; }
.issue.warning { fill: #9a6700; }
.empty-title { font: 16px Arial, sans-serif; fill: #555; }
</style>
</defs>"""
