from cutting_app.app.domain.part import PartSizes
from cutting_app.app.domain.placement import Rotation
from cutting_app.app.services.placement_calculator import calculate_placed_dimensions


def test_placed_dimensions_without_rotation_use_cutting_l_and_w():
	sizes = PartSizes(
		final_l_mm=300,
		final_w_mm=800,
		no_edge_l_mm=298,
		no_edge_w_mm=800,
		blank_l_mm=299,
		blank_w_mm=800,
		cutting_l_mm=299,
		cutting_w_mm=800,
	)

	placed = calculate_placed_dimensions(sizes, Rotation.DEG_0)

	assert placed.width_mm == 299
	assert placed.height_mm == 800


def test_placed_dimensions_with_90_rotation_swap_cutting_l_and_w():
	sizes = PartSizes(
		final_l_mm=300,
		final_w_mm=800,
		no_edge_l_mm=298,
		no_edge_w_mm=800,
		blank_l_mm=299,
		blank_w_mm=800,
		cutting_l_mm=299,
		cutting_w_mm=800,
	)

	placed = calculate_placed_dimensions(sizes, Rotation.DEG_90)

	assert placed.width_mm == 800
	assert placed.height_mm == 299