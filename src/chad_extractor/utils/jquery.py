#!/usr/bin/env python3

from . import array, input, result

import collections

def select_urls(obj: list[input.ChadResults], sort = False):
	"""
	Get all 'ChadResults.urls'.\n
	Returns a unique [sorted] list.
	"""
	tmp = []
	for entry in obj:
		tmp.extend(entry.urls)
	return array.unique(tmp, sort)

def group_by_url(obj: list[input.Input]) -> list[input.InputGrouped]:
	"""
	Group the input by 'Input.url'.
	"""
	grouped = collections.defaultdict(lambda: input.InputGrouped("", "", []))
	for entry in obj:
		grouped[entry.url].url = entry.url
		grouped[entry.url].key = entry.key
		grouped[entry.url].files.append(entry.file)
	tmp = []
	for entry in list(grouped.values()):
		entry.files = array.unique(entry.files, sort = True)
		tmp.append(entry)
	return tmp

# ----------------------------------------

def select_results(obj: list[result.Result | result.ResultPlaintext], sort = False):
	"""
	Get all 'Result.results[key]' or 'ResultPlaintext.results[key]'.\n
	Returns a unique [sorted] list.
	"""
	tmp = []
	for entry in obj:
		for key in entry.results:
			tmp.extend(entry.results[key])
	return array.unique(tmp, sort)

# ----------------------------------------

def sort_by_url(obj: list[result.Result]):
	"""
	Sort the results by 'Result.url'.
	"""
	return sorted(obj, key = lambda entry: entry.url.casefold())

def select_url(obj: list[result.Result], sort = False):
	"""
	Get all 'Result.url'.\n
	Returns a unique [sorted] list.
	"""
	tmp = []
	for entry in obj:
		tmp.append(entry.url)
	return array.unique(tmp, sort)

# ----------------------------------------

def sort_by_file(obj: list[result.ResultPlaintext]):
	"""
	Sort the results by 'ResultPlaintext.file'.
	"""
	return sorted(obj, key = lambda entry: entry.file.casefold())

def select_file(obj: list[result.ResultPlaintext], sort = False):
	"""
	Get all 'ResultPlaintext.file'.\n
	Returns a unique [sorted] list.
	"""
	tmp = []
	for entry in obj:
		tmp.append(entry.file)
	return array.unique(tmp, sort)

def select_files(obj: list[result.Result], sort = False):
	"""
	Get all 'Result.files'.\n
	Returns a unique [sorted] list.
	"""
	tmp = []
	for entry in obj:
		tmp.extend(entry.files)
	return array.unique(tmp, sort)

# ----------------------------------------

def select_by_file(obj: list[result.ResultPlaintext], file: str) -> list[result.ResultPlaintext]:
	"""
	Get all 'Result' for the specified file.
	"""
	tmp = []
	for entry in obj:
		if file == entry.file:
			tmp.append(entry)
			break
	return tmp

def select_by_files(obj: list[result.Result], file: str) -> list[result.Result]:
	"""
	Get all 'Result' for the specified file.
	"""
	tmp = []
	for entry in obj:
		if file in entry.files:
			tmp.append(entry)
	return tmp

def select_url_by_file(obj: list[result.Result], file: str, sort = False):
	"""
	Get all 'Result' for the specified file.\n
	Returns a unique [sorted] list.
	"""
	tmp = []
	for entry in obj:
		if file in entry.files:
			tmp.append(entry.url)
	return array.unique(tmp, sort)
