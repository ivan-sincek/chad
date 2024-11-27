#!/usr/bin/env python3

class Proxies:

	def __init__(self, proxies: list[str]):
		"""
		Class for rotating proxies in a round robin fashion.
		"""
		self.__proxies     = proxies
		self.__proxies_len = len(self.__proxies)
		self.__index       = 0
		self.__round_robin = False

	def is_empty(self):
		"""
		Returns 'True' if there are no proxies.
		"""
		return not self.__proxies

	def is_round_robin(self):
		"""
		This should be checked on each iteration.\n
		If a full round has been completed, return 'True' and reset the round robin flag; otherwise, return 'False'.
		"""
		current = self.__round_robin
		if current:
			self.__round_robin = False
		return current

	def get(self):
		"""
		Get a proxy in a round robin fashion.\n
		If a full round has been completed, set the round robin flag.\n
		Returns an empty string if there are no proxies.
		"""
		proxy = ""
		if self.__proxies:
			proxy = self.__proxies[self.__index]
			self.__index = (self.__index + 1) % self.__proxies_len
			if self.__index == 0:
				self.__round_robin = True
		return proxy

	def remove(self, proxy: str):
		"""
		Remove a proxy.\n
		Returns an empty message if the proxy does not exist.
		"""
		message = ""
		if proxy in self.__proxies:
			self.__proxies.pop(self.__proxies.index(proxy))
			self.__proxies_len -= 1
			message = f"Removing '{proxy}' due to an error or rate limiting | Proxies left: {self.__proxies_len}"
			self.__index = max(0, self.__index - 1)
		return message
