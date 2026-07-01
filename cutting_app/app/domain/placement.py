from enum import Enum


class Rotation(str, Enum):
	DEG_0 = "0"
	DEG_90 = "90"


class VisualSide(str, Enum):
	TOP = "top"
	RIGHT = "right"
	BOTTOM = "bottom"
	LEFT = "left"