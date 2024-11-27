#!/usr/bin/env python3

from . import array

import dataclasses, os, urllib.parse

__ENCODING = "ISO-8859-1"

@dataclasses.dataclass
class File:
	"""
	Class for storing file details.
	"""
	content: bytes = b""
	path   : str   = ""

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

def read_array(file: str) -> list[str]:
	"""
	Read a file line by line, and append the lines to a list.\n
	Whitespace will be stripped from each line, and empty lines will be removed.\n
	Returns a unique list.
	"""
	tmp = []
	with open(file, "r", encoding = __ENCODING) as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	return array.unique(tmp)

def write_binary_silent(content: bytes, out: str):
	"""
	Silently write a binary content to an output file.
	"""
	try:
		open(out, "wb").write(content)
	except Exception:
		pass

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

def get_url_filename(url: str, downloads_directory: str = ""):
	"""
	Derive a filename from a URL.\n
	If a duplicate exists, append a unique number to the filename.\n
	Returns the full path to the file.
	"""
	tmp = urllib.parse.urlsplit(url)
	base = tmp.path.strip("/").rsplit("/", 1)[-1]
	if not base:
		base = tmp.netloc
	base = os.path.join(downloads_directory, base)
	count = 0
	filename = base
	while os.path.isfile(filename):
		count += 1
		filename = f"{base} ({count})"
	return filename
