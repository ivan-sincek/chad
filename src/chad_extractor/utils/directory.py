#!/usr/bin/env python3

from . import array, file

import os

def exists(path: str):
	"""
	Returns 'True' if a path exists.
	"""
	return os.path.exists(path)

def is_directory(directory: str):
	"""
	Returns 'True' if the 'directory' exists and is a regular directory.
	"""
	return os.path.isdir(directory)

def validate(directory: str):
	"""
	Validate a directory.\n
	Success flag is 'True' if the directory has a read permission and is not empty.
	"""
	success = False
	message = ""
	if not os.access(directory, os.R_OK):
		message = f"\"{directory}\" does not have a read permission"
	elif not os.stat(directory).st_size > 0:
		message = f"\"{directory}\" is empty"
	else:
		success = True
	return success, message

def list_files(directory: str, sort = False):
	"""
	Get all valid files from a directory. Non-recursive.
	"""
	tmp = []
	for filename in os.listdir(directory):
		path = os.path.join(directory, filename)
		if file.validate_silent(path):
			tmp.append(path)
	return array.unique(tmp, sort)
