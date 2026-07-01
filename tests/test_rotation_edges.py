from cutting_app.app.domain.edge import EdgeSide
from cutting_app.app.domain.placement import Rotation, VisualSide
from cutting_app.app.services.edge_visual_mapper import map_edge_side_to_visual_side


def test_edges_are_drawn_on_expected_sides_without_rotation():
	assert map_edge_side_to_visual_side(EdgeSide.L1, Rotation.DEG_0) == VisualSide.TOP
	assert map_edge_side_to_visual_side(EdgeSide.W2, Rotation.DEG_0) == VisualSide.RIGHT
	assert map_edge_side_to_visual_side(EdgeSide.L2, Rotation.DEG_0) == VisualSide.BOTTOM
	assert map_edge_side_to_visual_side(EdgeSide.W1, Rotation.DEG_0) == VisualSide.LEFT


def test_edges_rotate_clockwise_with_part_when_rotated_90_degrees():
	assert map_edge_side_to_visual_side(EdgeSide.L1, Rotation.DEG_90) == VisualSide.RIGHT
	assert map_edge_side_to_visual_side(EdgeSide.W2, Rotation.DEG_90) == VisualSide.BOTTOM
	assert map_edge_side_to_visual_side(EdgeSide.L2, Rotation.DEG_90) == VisualSide.LEFT
	assert map_edge_side_to_visual_side(EdgeSide.W1, Rotation.DEG_90) == VisualSide.TOP