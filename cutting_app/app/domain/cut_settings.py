from dataclasses import dataclass


@dataclass(frozen=True)
class CutSettings:
    kerf_width_mm: float