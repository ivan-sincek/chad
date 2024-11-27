#!/usr/bin/env python3

import regex as re

def validate(query: str):
	"""
	Validate a regular expression.
	"""
	success = False
	message = ""
	try:
		re.compile(query)
		success = True
	except re.error:
		message = f"Invalid RegEx: {query}"
	return success, message

def validate_multiple(queries: list[str]):
	"""
	Validate multiple regular expressions.
	"""
	success = True
	message = ""
	for query in queries:
		success, message = validate(query)
		if not success:
			break
	return success, message
