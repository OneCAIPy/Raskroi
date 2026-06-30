from cutting_app.app.domain.part import PartInput, PartSizes


def calculate_part_sizes(part: PartInput) -> PartSizes:
	no_edge_l_mm = (
		part.l_mm
		- part.edges.W1.thickness_mm
		- part.edges.W2.thickness_mm
	)

	no_edge_w_mm = (
		part.w_mm
		- part.edges.L1.thickness_mm
		- part.edges.L2.thickness_mm
	)

	blank_l_mm = (
		no_edge_l_mm
		+ part.edges.W1.trimming_allowance_mm
		+ part.edges.W2.trimming_allowance_mm
	)

	blank_w_mm = (
		no_edge_w_mm
		+ part.edges.L1.trimming_allowance_mm
		+ part.edges.L2.trimming_allowance_mm
	)

	return PartSizes(
		final_l_mm=part.l_mm,
		final_w_mm=part.w_mm,
		no_edge_l_mm=no_edge_l_mm,
		no_edge_w_mm=no_edge_w_mm,
		blank_l_mm=blank_l_mm,
		blank_w_mm=blank_w_mm,
		cutting_l_mm=blank_l_mm,
		cutting_w_mm=blank_w_mm,
	)