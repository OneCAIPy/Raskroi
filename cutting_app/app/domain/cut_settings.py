from dataclasses import dataclass

from cutting_app.app.domain.cut_tree import CutDirection


@dataclass(frozen=True)
class CutSettings:
    kerf_width_mm: float
    initial_cut_direction: CutDirection = CutDirection.VERTICAL
