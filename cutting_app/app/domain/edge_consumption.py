from dataclasses import dataclass, field

from cutting_app.app.domain.edge import EdgeSide


@dataclass(frozen=True)
class EdgeSegment:
	part_number: str
	source_part_number: str
	part_name: str
	side: EdgeSide
	material_name: str
	thickness_mm: float
	base_length_mm: float
	tape_overhang_mm: float

	@property
	def total_length_mm(self) -> float:
		return self.base_length_mm + self.tape_overhang_mm


@dataclass(frozen=True)
class EdgeMaterialConsumption:
	material_name: str
	thickness_mm: float
	segment_count: int
	base_length_mm: float
	overhang_length_mm: float
	total_length_mm: float


@dataclass(frozen=True)
class EdgeConsumption:
	segments: tuple[EdgeSegment, ...] = field(default_factory=tuple)
	by_material: tuple[EdgeMaterialConsumption, ...] = field(default_factory=tuple)
	segment_count: int = 0
	base_length_mm: float = 0
	overhang_length_mm: float = 0
	total_length_mm: float = 0
