#!/usr/bin/env python3

import colorama, datetime, json, termcolor, typing

colorama.init(autoreset = True)

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

def jdump(data: typing.Any):
	"""
	Serialize a data to a JSON string.
	"""
	return json.dumps(data, indent = 4, ensure_ascii = False)
