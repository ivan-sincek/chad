
#!/usr/bin/env python3

import dataclasses, json

@dataclasses.dataclass
class Input:
	"""
	Class for temporarily storing an input used for extraction or validation.
	"""
	url : str
	key : str
	file: str

@dataclasses.dataclass
class InputGrouped:
	"""
	Class for storing an input used for extraction or validation grouped by URL.
	"""
	url  : str
	key  : str
	files: list[str]

# ----------------------------------------

@dataclasses.dataclass
class ChadResults:
	"""
	Class for storing Chad results.
	"""
	query: str       = ""
	proxy: str       = ""
	urls : list[str] = dataclasses.field(default_factory = list)

def deserialize_chad_results(chad_results_json: str) -> tuple[list[ChadResults] | None, str]:
	"""
	Deserialize Chad results from a JSON string.\n
	Returns 'None' and an error message on failure.
	"""
	results = None
	message = ""
	try:
		tmp = json.loads(chad_results_json)
		for i in range(len(tmp)):
			tmp[i] = ChadResults(**tmp[i])
		results = tmp
	except Exception:
		message = "Cannot deserialize Chad results"
	return results, message
