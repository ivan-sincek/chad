#!/usr/bin/env python3

from . import array

import os

__ENCODING = "ISO-8859-1"

def is_file(file: str):
	"""
	Returns 'True' if the 'file' exists and is a regular file.
	"""
	return os.path.isfile(file)

def validate(file: str):
	"""
	Validate a file.\n
	Success flag is 'True' if the file has a read permission and is not empty.
	"""
	success = False
	message = ""
	if not os.access(file, os.R_OK):
		message = f"\"{file}\" does not have a read permission"
	elif not os.stat(file).st_size > 0:
		message = f"\"{file}\" is empty"
	else:
		success = True
	return success, message

def validate_silent(file: str):
	"""
	Silently validate a file.\n
	Returns 'True' if the 'file' exists, is a regular file, has a read permission, and is not empty.
	"""
	return os.path.isfile(file) and os.access(file, os.R_OK) and os.stat(file).st_size > 0

def read(file: str):
	"""
	Read a file as text.\n
	Whitespace will be stripped from the text.
	"""
	return open(file, "r", encoding = __ENCODING).read().strip()

def read_array(file: str, sort = False):
	"""
	Read a file line by line, and append the lines to a list.\n
	Whitespace will be stripped from each line, and empty lines will be removed.\n
	Returns a unique [sorted] list.
	"""
	tmp = []
	with open(file, "r", encoding = __ENCODING) as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	return array.unique(tmp, sort)

def overwrite(text: str, out: str):
	"""
	Write a text to an output file.\n
	If the output file exists, prompt to overwrite it.
	"""
	confirm = "yes"
	if os.path.isfile(out):
		print(f"'{out}' already exists")
		confirm = input("Overwrite the output file (yes): ")
	if confirm.lower() in ["yes", "y"]:
		try:
			open(out, "w").write(text)
			print(f"Results have been saved to '{out}'")
		except FileNotFoundError:
			print(f"Cannot save the results to '{out}'")

def write_silent(text: str, out: str):
	"""
	Silently write a text to an output file.
	"""
	try:
		open(out, "w").write(text)
	except Exception:
		pass
