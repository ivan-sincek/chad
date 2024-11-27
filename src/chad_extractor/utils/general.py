#!/usr/bin/env python3

import colorama, datetime, json, termcolor, typing

colorama.init(autoreset = True)

__ENCODINGS = ["ISO-8859-1", "UTF-8"]

def decode(bytes: bytes):
	"""
	Returns an empty string and an error message on failure.
	"""
	text = ""
	message = ""
	for encoding in __ENCODINGS:
		try:
			text = bytes.decode(encoding)
			message = ""
			break
		except Exception as ex:
			message = str(ex)
	return text, message

def to_float(value: str):
	"""
	Returns 'None' on failure.
	"""
	tmp = None
	try:
		tmp = float(value)
	except ValueError:
		pass
	return tmp

def jdump(data: typing.Any):
	"""
	Serialize a data to a JSON string.
	"""
	return json.dumps(data, indent = 4, ensure_ascii = False)

# ----------------------------------------

def get_timestamp(message):
	"""
	Get the current timestamp.
	"""
	return f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}"

def print_error(message: str):
	"""
	Print an error message.
	"""
	print(f"ERROR: {message}")

def print_cyan(message: str):
	"""
	Print a message in cyan color.
	"""
	termcolor.cprint(message, "cyan")

def print_green(message: str):
	"""
	Print a message in green color.
	"""
	termcolor.cprint(message, "green")

def print_yellow(message: str):
	"""
	Print a message in yellow color.
	"""
	termcolor.cprint(message, "yellow")

def print_red(message: str):
	"""
	Print a message in red color.
	"""
	termcolor.cprint(message, "red")

def print_magenta(message: str):
	"""
	Print a message in magenta color.
	"""
	termcolor.cprint(message, "magenta")
