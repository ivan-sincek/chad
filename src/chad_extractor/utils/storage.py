#!/usr/bin/env python3

from . import array, file, general, input, jquery, result, template

import multiprocessing.managers, regex as re

class MyManager(multiprocessing.managers.BaseManager):
	pass

class Shared:

	def __init__(
		self,
		template   : template.Template,
		input      : list[str],
		plaintext  : bool,
		excludes   : list[str],
		debug      : bool
	):
		"""
		Class for managing a shared storage in multiprocessing.
		"""
		self.__template        = template
		self.__input           = input
		self.__plaintext       = plaintext
		self.__excludes        = excludes
		self.__debug           = debug
		self.__flags           = re.MULTILINE | re.IGNORECASE
		self.__stage           = result.Stage.EXTRACTION
		self.__results         = result.Results()

	def start_validation(self):
		"""
		Start validation.
		"""
		self.__stage = result.Stage.VALIDATION

	def is_validation_started(self):
		"""
		Check if validation has started.
		"""
		return self.__stage == result.Stage.VALIDATION

	def get_input(self) -> list[input.InputGrouped]:
		"""
		Get the input used for extraction or validation.
		"""
		return self.__input

	def has_input(self):
		"""
		Check if there is any input to be used for extraction or validation.
		"""
		return bool(self.get_input())

	def append_error(self, result: result.Result | result.ResultPlaintext):
		"""
		Append a result to the error list.
		"""
		self.__results.results[self.__stage].error.append(result)

	def get_error(self):
		"""
		Get the error list.
		"""
		return self.__results.results[self.__stage].error

	def has_error(self):
		"""
		Check if there is any result in the error list.
		"""
		return bool(self.get_error())

	def append_success(self, result: result.Result | result.ResultPlaintext):
		"""
		Append a result to the success list.
		"""
		self.__results.results[self.__stage].success.append(result)

	def get_success(self):
		"""
		Get the success list.
		"""
		return self.__results.results[self.__stage].success

	def has_success(self):
		"""
		Check if there is any result in the success list.
		"""
		return bool(self.get_success())

	def get_results(self):
		"""
		Get all results.
		"""
		return self.__results

	def require_playwright(self):
		"""
		Check if Playwright's headless browser is required and set the browser wait time to zero.\n
		Applies only for validation.\n
		Returns 'True' if required and '0'.
		"""
		playwright, playwright_wait = False, 0
		for value in self.__template.entries.values():
			if value.validate_browser:
				playwright = True
				break
		return playwright, playwright_wait

	def get_playwright(self, key: str):
		"""
		Check if Playwright's headless browser is required and get the browser wait time for the specified key.\n
		Applies only for validation.\n
		Returns 'True' if required and the browser wait time.
		"""
		return self.__template.entries[key].validate_browser, self.__template.entries[key].validate_browser_wait

	def parse_template(self):
		"""
		During extraction, remove all template entries without the 'extract' RegEx.\n
		During validation, remove all template entries without the 'validate' RegEx.\n
		Returns 'False' if no entries are left.
		"""
		for key in list(self.__template.entries.keys()):
			if (self.__stage == result.Stage.EXTRACTION and not self.__template.entries[key].extract) or (self.__stage == result.Stage.VALIDATION and not self.__template.entries[key].validate):
				self.__template.entries.pop(key)
		return bool(self.__template.entries)

	def parse_input(self):
		"""
		Parse the input used for extraction or validation.
		"""
		tmp = []
		if not self.is_validation_started():
			if not self.__plaintext:
				for path in self.__input:
					chad_results, message = input.deserialize_chad_results(file.read(path))
					if message:
						if self.__debug:
							general.print_red(f"{message} from \"{path}\"")
					else:
						for url in jquery.select_urls(chad_results):
							tmp.append(input.Input(url, "", path))
			else:
				for path in self.__input:
					results = self.parse_response(content = file.read(path)) # plaintext files are treated like server responses
					if results:
						self.append_success(result.ResultPlaintext(path, results))
				return self.has_success()
		else:
			if not self.__plaintext:
				for entry in self.__results.results[result.Stage.EXTRACTION].success: # extracted data
					for key in entry.results:
						if key in self.__template.entries:
							for url in entry.results[key]:
								for path in entry.files:
									tmp.append(input.Input(url, key, path))
			else:
				for entry in self.__results.results[result.Stage.EXTRACTION].success: # extracted data
					for key in entry.results:
						if key in self.__template.entries:
							for url in entry.results[key]:
								tmp.append(input.Input(url, key, entry.file))
		self.__input = jquery.group_by_url(tmp)
		return self.has_input()

	def parse_response(self, content: str, key = "") -> dict[str, list[str]] | bool:
		"""
		Parse an HTTP response content as a result of extraction or validation.
		"""
		tmp = {}
		try:
			if not self.is_validation_started():
				if self.__excludes:
					for query in self.__excludes:
						content = re.sub(query, "", content, flags = self.__flags)
				for key, value in self.__template.entries.items():
					matches = re.findall(value.extract, content, flags = self.__flags)
					if matches:
						if value.extract_prepend or value.extract_append:
							for i in range(len(matches)):
								matches[i] = value.extract_prepend + matches[i] + value.extract_append
						tmp[key] = array.unique(matches, sort = True)
			elif re.search(self.__template.entries[key].validate, content, flags = self.__flags):
				tmp = True
		except (re.error, KeyError) as ex:
			if self.__debug:
				general.print_red(str(ex))
		return tmp

	def get_headers(self, key = "", with_cookies = False) -> dict[str, str]:
		"""
		Get validation HTTP request headers for the specified key.\n
		Returns an empty dictionary if the specified key does not exist or is empty.
		"""
		headers = {}
		if key and key in self.__template.entries:
			for name, value in self.__template.entries[key].validate_headers.items():
				headers[name.lower()] = value
			if with_cookies:
				cookies = self.get_cookies(key)
				if cookies:
					headers["cookie"] = ("; ").join(f"{name}={value}" for name, value in cookies.items()) # for APIRequestContext.get()
		return headers

	def get_cookies(self, key = "") -> dict[str, str]:
		"""
		Get validation HTTP cookies for the specified key.\n
		Returns an empty dictionary if the specified key does not exist or is empty.
		"""
		cookies = {}
		if key and key in self.__template.entries:
			for name, value in self.__template.entries[key].validate_cookies.items():
				cookies[name.lower()] = value
		return cookies
