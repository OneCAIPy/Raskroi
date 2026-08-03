import pytest

from cutting_app.app.domain.cut_settings import CutSettings
from cutting_app.app.domain.edge import EdgeSet
from cutting_app.app.domain.part import PartInput
from cutting_app.app.domain.sheet import SheetInput
from cutting_app.app.domain.sheet_limit_search import (
	SheetLimitSearchSettings,
	SheetLimitSearchStatus,
)
from cutting_app.app.services.cutting_result_validator import validate_cutting_result
from cutting_app.app.services.guillotine_sheet_limit_search import (
	search_guillotine_sheet_limit,
)
from tests.basis_agt_3019_fixture import (
	build_basis_agt_3019_parts,
	build_basis_agt_3019_settings,
	build_basis_agt_3019_sheets,
)


def _part(number: str, l_mm: float, w_mm: float) -> PartInput:
	return PartInput(
		number=number,
		name=f"Деталь {number}",
		l_mm=l_mm,
		w_mm=w_mm,
		quantity=1,
		edges=EdgeSet(),
		rotation_allowed=True,
	)


@pytest.mark.parametrize(
	("field_name", "value"),
	[
		("sheet_limit", 0),
		("beam_width", 0),
		("branch_factor", 0),
		("max_variants", 0),
	],
)
def test_sheet_limit_search_settings_require_positive_values(
	field_name: str,
	value: int,
) -> None:
	values = {
		"sheet_limit": 1,
		"beam_width": 8,
		"branch_factor": 4,
		"max_variants": 2,
	}
	values[field_name] = value

	with pytest.raises(ValueError):
		SheetLimitSearchSettings(**values)


def test_sheet_limit_search_proves_only_the_area_lower_bound() -> None:
	report = search_guillotine_sheet_limit(
		parts=[_part("1", 101, 100)],
		sheets=[SheetInput(name="Лист", width_mm=100, height_mm=100)],
		settings=CutSettings(kerf_width_mm=2),
		search_settings=SheetLimitSearchSettings(sheet_limit=1),
	)

	assert report.status == SheetLimitSearchStatus.PROVEN_IMPOSSIBLE_BY_AREA
	assert report.is_proven_impossible is True
	assert report.found is False
	assert report.evaluated_state_count == 0
	assert report.result is None


def test_sheet_limit_search_finds_and_validates_complete_layout() -> None:
	search_settings = SheetLimitSearchSettings(
		sheet_limit=1,
		beam_width=16,
		branch_factor=6,
		max_variants=4,
	)
	arguments = {
		"parts": [_part("1", 50, 100), _part("2", 50, 100)],
		"sheets": [SheetInput(name="Лист", width_mm=102, height_mm=100)],
		"settings": CutSettings(kerf_width_mm=2),
		"search_settings": search_settings,
	}

	first = search_guillotine_sheet_limit(**arguments)
	second = search_guillotine_sheet_limit(**arguments)

	assert first == second
	assert first.status == SheetLimitSearchStatus.FOUND
	assert first.found is True
	assert first.is_proven_impossible is False
	assert first.result is not None
	assert first.result.metrics.sheet_count == 1
	assert first.result.metrics.placed_part_count == 2
	assert first.result.metrics.unplaced_part_count == 0
	assert validate_cutting_result(first.result) == []


def test_unsuccessful_bounded_search_does_not_claim_global_impossibility() -> None:
	report = search_guillotine_sheet_limit(
		parts=[_part("1", 60, 60), _part("2", 60, 60)],
		sheets=[SheetInput(name="Лист", width_mm=100, height_mm=100)],
		settings=CutSettings(kerf_width_mm=2),
		search_settings=SheetLimitSearchSettings(
			sheet_limit=1,
			beam_width=8,
			branch_factor=4,
			max_variants=2,
		),
	)

	assert report.status == SheetLimitSearchStatus.NOT_FOUND_WITHIN_BUDGET
	assert report.found is False
	assert report.is_proven_impossible is False
	assert report.result is None
	assert report.best_partial_result is not None
	assert report.best_partial_result.metrics.placed_part_count == 1
	assert report.best_partial_result.metrics.unplaced_part_count == 1


def test_basis_reference_12_sheet_check_has_explicit_bounded_status() -> None:
	report = search_guillotine_sheet_limit(
		parts=build_basis_agt_3019_parts(),
		sheets=build_basis_agt_3019_sheets(),
		settings=build_basis_agt_3019_settings(),
		search_settings=SheetLimitSearchSettings(
			sheet_limit=12,
			beam_width=4,
			branch_factor=2,
			max_variants=1,
		),
	)

	assert report.status == SheetLimitSearchStatus.NOT_FOUND_WITHIN_BUDGET
	assert report.is_proven_impossible is False
	assert report.evaluated_variant_count == 1
	assert report.evaluated_state_count > 0
	assert report.pruned_state_count > 0
	assert 0 < report.deepest_search_prefix_part_count < 93
	assert report.best_partial_result is not None
	assert report.best_partial_result.metrics.sheet_count == 12
	assert report.best_partial_result.metrics.placed_part_count < 93
	assert validate_cutting_result(report.best_partial_result) == []
