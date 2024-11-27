#!/usr/bin/env python3

import regex as re

__FLAGS = re.MULTILINE | re.IGNORECASE

def has_site(text: str):
	"""
	Check if there are any matches in a text using the '(?<!in|\-)site\:' RegEx pattern.
	"""
	return bool(re.search(r"(?<!in|\-)site\:", text, flags = __FLAGS))

def get_blacklist():
	"""
	Get a blacklist RegEx to exclude websites containing Google Dorks from the results.
	"""
	blacklist = ["kb.cert.org", "exploit-db.com"]
	# ------------------------------------
	for keyword in ["dork", "hack"]:
		for sep in ["", "+", "-", "_", "%20"]:
			blacklist.append(f"google{sep}{keyword}")
	# ------------------------------------
	blacklist = [entry.replace(".", "\\.").replace("/", "\\/").replace("?", "\\?") for entry in blacklist]
	blacklist = ("|").join(blacklist)
	blacklist = f"(?:{blacklist})"
	return blacklist

def filter_blacklist(array: list[str], blacklist: str) -> list[str]:
	"""
	Remove all blacklisted values from a list using the specified RegEx pattern.
	"""
	tmp = []
	for entry in array:
		if not re.search(blacklist, entry, flags = __FLAGS):
			tmp.append(entry)
	return tmp
