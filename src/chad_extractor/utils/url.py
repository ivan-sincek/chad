#!/usr/bin/env python3

import urllib.parse

__URL_SCHEME_WHITELIST = ["http", "https", "socks4", "socks4h", "socks5", "socks5h"]
__MIN_PORT_NUM         = 1
__MAX_PORT_NUM         = 65535

def validate(url: str):
	"""
	Validate a URL.
	"""
	success = False
	message = ""
	tmp = urllib.parse.urlsplit(url)
	if not tmp.scheme:
		message = f"URL scheme is required: {url}"
	elif tmp.scheme not in __URL_SCHEME_WHITELIST:
		message = f"Supported URL schemes are 'http[s]', 'socks4[h]', and 'socks5[h]': {url}"
	elif not tmp.netloc:
		message = f"Invalid domain name: {url}"
	elif tmp.port and (tmp.port < __MIN_PORT_NUM or tmp.port > __MAX_PORT_NUM):
		message = f"Port number is out of range: {url}"
	else:
		success = True
	return success, message

def normalize(url: str):
	"""
	Normalize a URL.
	"""
	return urllib.parse.urlsplit(url).geturl()
