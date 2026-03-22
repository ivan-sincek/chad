#!/usr/bin/env python3

import dataclasses, enum

class Stage(enum.Enum):
	"""
	Enum containing stages.
	"""
	EXTRACTION = "extraction"
	VALIDATION = "validation"

@dataclasses.dataclass
class Result:
	"""
	Class for storing a result.
	"""
	url    : str
	files  : list[str]
	results: dict[str, list[str]] = dataclasses.field(default_factory = dict)

@dataclasses.dataclass
class ResultPlaintext:
	"""
	Class for storing a plaintext result.
	"""
	file   : str
	results: dict[str, list[str]] = dataclasses.field(default_factory = dict)

@dataclasses.dataclass
class StageResults:
	"""
	Class for storing results of a single stage.
	"""
	success: list[Result | ResultPlaintext] = dataclasses.field(default_factory = list)
	error  : list[Result | ResultPlaintext] = dataclasses.field(default_factory = list)

@dataclasses.dataclass
class Results:
	"""
	Class for storing results of multiple stages.
	"""
	results: dict[Stage, StageResults] = dataclasses.field(default_factory = dict)

	def __post_init__(self):
		self.results[Stage.EXTRACTION] = StageResults()
		self.results[Stage.VALIDATION] = StageResults()
