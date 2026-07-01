from cutting_app.app.domain.edge import EdgeSide
from cutting_app.app.domain.placement import Rotation, VisualSide


_EDGE_SIDE_TO_VISUAL_SIDE = {
	Rotation.DEG_0: {
		EdgeSide.L1: VisualSide.TOP,
		EdgeSide.W2: VisualSide.RIGHT,
		EdgeSide.L2: VisualSide.BOTTOM,
		EdgeSide.W1: VisualSide.LEFT,
	},
	Rotation.DEG_90: {
		EdgeSide.L1: VisualSide.RIGHT,
		EdgeSide.W2: VisualSide.BOTTOM,
		EdgeSide.L2: VisualSide.LEFT,
		EdgeSide.W1: VisualSide.TOP,
	},
}


def map_edge_side_to_visual_side(
	side: EdgeSide,
	rotation: Rotation,
) -> VisualSide:
	return _EDGE_SIDE_TO_VISUAL_SIDE[rotation][side]