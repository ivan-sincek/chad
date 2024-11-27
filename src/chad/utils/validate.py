#!/usr/bin/env python3

from . import config, directory, file, general

import argparse, nagooglesearch, sys

class MyArgParser(argparse.ArgumentParser):

	def print_help(self):
		print(f"Chad {config.APP_VERSION} ( github.com/ivan-sincek/chad )")
		print("")
		print("Usage:   chad -q queries     [-s site         ] [-x proxies    ] [-o out         ]")
		print("Example: chad -q queries.txt [-s *.example.com] [-x proxies.txt] [-o results.json]")
		print("")
		print("DESCRIPTION")
		print("    Search Google Dorks like Chad")
		print("QUERIES")
		print("    File containing Google Dorks or a single query to use")
		print("    -q, --queries = queries.txt | intext:password | \"ext:tar OR ext:zip\" | etc.")
		print("SITE")
		print("    Domain[s] to search")
		print("    -s, --site = example.com | sub.example.com | *.example.com | \"*.example.com -www\" | etc.")
		print("TIME")
		print("    Get results not older than the specified time in months")
		print("    -t, --time =  6 | 12 | 24 | etc.")
		print("TOTAL RESULTS")
		print("    Total number of unique results")
		print("    Default: 100")
		print("    -tr, --total-results = 200 | etc.")
		print("PAGE RESULTS")
		print("    Number of results per page - capped at 100 by Google")
		print("    Default: randint(70, 100)")
		print("    -pr, --page-results = 50 | etc.")
		print("MINIMUM QUERIES")
		print("    Minimum sleep time in seconds between Google queries")
		print("    Default: 75")
		print("    -min-q, --minimum-queries = 120 | etc.")
		print("MAXIMUM QUERIES")
		print("    Maximum sleep time between Google queries")
		print("    Default: minimum + 50")
		print("    -max-q, --maximum-queries = 180 | etc.")
		print("MINIMUM PAGES")
		print("    Minimum sleep time between Google pages")
		print("    Default: 15")
		print("    -min-p, --minimum-pages = 30 | etc.")
		print("MAXIMUM PAGES")
		print("    Maximum sleep time between Google pages")
		print("    Default: minimum + 10")
		print("    -max-p, --maximum-pages = 60 | etc.")
		print("USER AGENTS")
		print("    User agents to use")
		print("    Default: random-all")
		print("    -a, --user-agents = user_agents.txt | random(-all) | curl/3.30.1 | etc.")
		print("PROXIES")
		print("    File containing web proxies or a single web proxy to use")
		print("    -x, --proxies = proxies.txt | http://127.0.0.1:8080 | etc.")
		print("DIRECTORY")
		print("    Downloads directory")
		print("    All downloaded files will be saved in this directory")
		print("    -dir, --directory = downloads | etc.")
		print("THREADS")
		print("    Number of files to download in parallel")
		print("    Default: 5")
		print("    -th, --threads = 20 | etc.")
		print("OUT")
		print("    Output file")
		print("    -o, --out = results.json | etc.")
		print("NO SLEEP ON START")
		print("    Disable the safety feature to prevent triggering rate limits by accident")
		print("    -nsos, --no-sleep-on-start")
		print("DEBUG")
		print("    Enable debug output")
		print("    -dbg, --debug")

	def error(self, message):
		if len(sys.argv) > 1:
			print("Missing a mandatory option (-q) and/or optional (-s, -t, -tr, -pr, -min-q, -max-q, -min-p, -max-p, -a, -x, -dir, -th, -o, -nsos, -dbg)")
			print("Use -h or --help for more info")
		else:
			self.print_help()
		exit()

class Validate:

	def __init__(self):
		"""
		Class for validating and managing CLI arguments.
		"""
		self.__parser = MyArgParser()
		self.__parser.add_argument("-q"    , "--queries"          , required = True , type   = str         , default = ""   )
		self.__parser.add_argument("-s"    , "--site"             , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-t"    , "--time"             , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-tr"   , "--total-results"    , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-pr"   , "--page-results"     , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-min-q", "--minimum-queries"  , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-max-q", "--maximum-queries"  , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-min-p", "--minimum-pages"    , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-max-p", "--maximum-pages"    , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-a"    , "--user-agents"      , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-x"    , "--proxies"          , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-dir"  , "--directory"        , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-th"   , "--threads"          , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-o"    , "--out"              , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-nsos" , "--no-sleep-on-start", required = False, action = "store_true", default = False)
		self.__parser.add_argument("-dbg"  , "--debug"            , required = False, action = "store_true", default = False)

	def validate_args(self):
		"""
		Validate and return the CLI arguments.
		"""
		self.__success = True
		self.__args = self.__parser.parse_args()
		self.__validate_queries()
		self.__validate_time()
		self.__validate_total_results()
		self.__validate_page_results()
		self.__validate_minimum_queries()
		self.__validate_maximum_queries()
		self.__validate_minimum_pages()
		self.__validate_maximum_pages()
		self.__validate_user_agents()
		self.__validate_proxies()
		self.__validate_directory()
		self.__validate_threads()
		return self.__success, self.__args

	def __error(self, message: str):
		"""
		Set the success flag to 'False' to prevent the main task from executing, and print an error message.
		"""
		self.__success = False
		general.print_error(message)

	# ------------------------------------

	def __validate_queries(self):
		tmp = []
		if file.is_file(self.__args.queries):
			success, message = file.validate(self.__args.queries)
			if not success:
				self.__error(message)
			else:
				tmp = file.read_array(self.__args.queries)
				if not tmp:
					self.__error(f"No Google Dorks were found in \"{self.__args.queries}\"")
		else:
			tmp = [self.__args.queries]
		self.__args.queries = tmp

	def __validate_time(self):
		tmp = 0
		if self.__args.time:
			if not self.__args.time.isdigit():
				self.__error("Number of months must be numeric")
			else:
				tmp = int(self.__args.time)
				if tmp <= 0:
					self.__error("Number of months must be greater than zero")
		self.__args.time = tmp

	def __validate_total_results(self):
		tmp = 100
		if self.__args.total_results:
			if not self.__args.total_results.isdigit():
				self.__error("Total number of unique results must be numeric")
			else:
				tmp = int(self.__args.total_results)
				if tmp <= 0:
					self.__error("Total number of unique results must be greater than zero")
		self.__args.total_results = tmp

	def __validate_page_results(self):
		tmp = 0
		if self.__args.page_results:
			if not self.__args.page_results.isdigit():
				self.__error("Number of results per page must be numeric")
			else:
				tmp = int(self.__args.page_results)
				if tmp < 1 or tmp > 100:
					self.__error("Number of results per page must be between 1 and 100")
		self.__args.page_results = tmp

	def __validate_minimum_queries(self):
		tmp = 75
		if self.__args.minimum_queries:
			if not self.__args.minimum_queries.isdigit():
				self.__error("Minimum sleep time between Google queries must be numeric")
			else:
				tmp = int(self.__args.minimum_queries)
				if tmp <= 0:
					self.__error("Minimum sleep time between Google queries must be greater than zero")
		self.__args.minimum_queries = tmp

	def __validate_maximum_queries(self):
		tmp = self.__args.minimum_queries + 50
		if self.__args.maximum_queries:
			if not self.__args.maximum_queries.isdigit():
				self.__error("Maximum sleep time between Google queries must be numeric")
			else:
				tmp = int(self.__args.maximum_queries)
				if tmp <= 0:
					self.__error("Maximum sleep time between Google queries must be greater than zero")
		self.__args.maximum_queries = tmp

	def __validate_minimum_pages(self):
		tmp = 15
		if self.__args.minimum_pages:
			if not self.__args.minimum_pages.isdigit():
				self.__error("Minimum sleep time between Google pages must be numeric")
			else:
				tmp = int(self.__args.minimum_pages)
				if tmp <= 0:
					self.__error("Minimum sleep time between Google pages must be greater than zero")
		self.__args.minimum_pages = tmp

	def __validate_maximum_pages(self):
		tmp = self.__args.minimum_pages + 10
		if self.__args.maximum_pages:
			if not self.__args.maximum_pages.isdigit():
				self.__error("Maximum sleep time between Google pages must be numeric")
			else:
				tmp = int(self.__args.maximum_pages)
				if tmp <= 0:
					self.__error("Maximum sleep time between Google pages must be greater than zero")
		self.__args.maximum_pages = tmp

	def __validate_user_agents(self):
		tmp = nagooglesearch.get_all_user_agents()
		if self.__args.user_agents:
			if file.is_file(self.__args.user_agents):
				success, message = file.validate(self.__args.user_agents)
				if not success:
					self.__error(message)
				else:
					tmp = file.read_array(self.__args.user_agents)
					if not tmp:
						self.__error(f"No user agents were found in \"{self.__args.user_agents}\"")
			else:
				lower = self.__args.user_agents.lower()
				if lower == "random-all":
					pass
				elif lower == "random":
					tmp = [nagooglesearch.get_random_user_agent()]
				else:
					tmp = [self.__args.user_agents]
		self.__args.user_agents = tmp

	def __validate_proxies(self):
		tmp = []
		if self.__args.proxies:
			if file.is_file(self.__args.proxies):
				success, message = file.validate(self.__args.proxies)
				if not success:
					self.__error(message)
				else:
					tmp = file.read_array(self.__args.proxies)
					if not tmp:
						self.__error(f"No web proxies were found in \"{self.__args.proxies}\"")
			else:
				tmp = [self.__args.proxies]
		self.__args.proxies = tmp

	def __validate_directory(self):
		if self.__args.directory:
			if not directory.is_directory(self.__args.directory):
				self.__error(f"\"{self.__args.directory}\" does not exist or is not a directory")

	def __validate_threads(self):
		tmp = 5
		if self.__args.threads:
			if not self.__args.threads.isdigit():
				self.__error("Number of files to download in parallel must be numeric")
			else:
				tmp = int(self.__args.threads)
				if tmp <= 0:
					self.__error("Number of files to download in parallel must be greater than zero")
		self.__args.threads = tmp
