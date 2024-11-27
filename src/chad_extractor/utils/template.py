#!/usr/bin/env python3

import dataclasses, json

@dataclasses.dataclass
class TemplateEntry:
	"""
	Class for storing a single entry of Chad Extractor template.
	"""
	extract              : str
	extract_prepend      : str            = ""
	extract_append       : str            = ""
	validate             : str            = ""
	validate_browser     : bool           = False
	validate_browser_wait: float          = 0
	validate_headers     : dict[str, str] = dataclasses.field(default_factory = dict)
	validate_cookies     : dict[str, str] = dataclasses.field(default_factory = dict)

@dataclasses.dataclass
class Template:
	"""
	Class for storing a Chad Extractor template.
	"""
	entries: dict[str, TemplateEntry] = dataclasses.field(default_factory = dict)

# ----------------------------------------

def deserialize(template_json: str) -> tuple[Template | None, str]:
	"""
	Deserialize a Chad Extractor template from a JSON string.\n
	Returns 'None' and an error message on failure.
	"""
	template = Template()
	message = ""
	try:
		tmp = json.loads(template_json)
		for key in tmp.keys():
			template.entries[key] = TemplateEntry(**tmp[key])
	except Exception:
		template = None
		message = "Cannot deserialize the template"
	return template, message
