#!/usr/bin/env python3

def unique(array: list):
	"""
	Remove duplicates from a list.
	"""
	seen = set()
	return [x for x in array if not (x in seen or seen.add(x))]
