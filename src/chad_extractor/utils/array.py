#!/usr/bin/env python3

def unique(array: list[str], sort = False):
	"""
	Unique sort a list in ascending order.
	"""
	seen = set()
	array = [x for x in array if not (x in seen or seen.add(x))]
	if sort and array:
		array = sorted(array, key = str.casefold)
	return array
