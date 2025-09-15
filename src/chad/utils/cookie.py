#!/usr/bin/env python3

import regex as re

def get_key_value(cookie: str):
	"""
	Get a key-value pair from an HTTP cookie.\n
	Returns an empty key-value pair on failure.
	"""
	key = ""; value = ""
	if re.search(r"^[^\=\;]+\=[^\;]+$", cookie):
		key, value = cookie.split("=", 1)
	return key.strip(), value.strip()
