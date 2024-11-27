#!/usr/bin/env python3

from . import config, directory, file, general, grep, template, url

import argparse, nagooglesearch, sys

class MyArgParser(argparse.ArgumentParser):

	def print_help(self):
		print(f"Chad Extractor {config.APP_VERSION} ( github.com/ivan-sincek/chad )")
		print("")
		print("Usage:   chad-extractor -t template      -res results      -o out         [-s sleep] [-rs random-sleep]")
		print("Example: chad-extractor -t template.json -res chad_results -o report.json [-s 1.5  ] [-rs             ]")
		print("")
		print("DESCRIPTION")
		print("    Extract and validate data from Chad results or plaintext files")
		print("TEMPLATE")
		print("    File containing extraction and validation details")
		print("    -t, --template = template.json | etc.")
		print("RESULTS")
		print("    Directory containing Chad results or plaintext files, or a single file")
		print(f"    If a directory is specified, files ending with '{config.REPORT_EXTENSION}' will be ignored")
		print("    -res, --results = chad_results | results.json | urls.txt | etc.")
		print("PLAINTEXT")
		print("    Treat all the results as plaintext files / server responses")
		print("    -pt, --plaintext")
		print("EXCLUDES")
		print("    File containing regular expressions or a single regular expression to exclude content from the page")
		print("    Applies only for extraction")
		print("    -e, --excludes = regexes.txt | \"<div id=\\\"seo\\\">.+?<\\/div>\" | etc.")
		print("PLAYWRIGHT")
		print("    Use Playwright's headless browser")
		print("    Applies only for extraction")
		print("    -p, --playwright")
		print("PLAYWRIGHT WAIT")
		print("    Wait time in seconds before fetching the page content")
		print("    Applies only for extraction")
		print("    -pw, --playwright-wait = 0.5 | 2 | 4 | etc.")
		print("CONCURRENT REQUESTS")
		print("    Number of concurrent requests")
		print("    Default: 15")
		print("    -cr, --concurrent-requests = 30 | 45 | etc.")
		print("CONCURRENT REQUESTS PER DOMAIN")
		print("    Number of concurrent requests per domain")
		print("    Default: 5")
		print("    -crd, --concurrent-requests-domain = 10 | 15 | etc.")
		print("SLEEP")
		print("    Sleep time in seconds between two consecutive requests to the same domain")
		print("    -s, --sleep = 1.5 | 3 | etc.")
		print("RANDOM SLEEP")
		print("    Randomize the sleep time between requests to vary between '0.5 * sleep' and '1.5 * sleep'")
		print("    -rs, --random-sleep")
		print("AUTO THROTTLE")
		print("    Auto throttle concurrent requests based on the load and latency")
		print("    Sleep time is still respected")
		print("    -at, --auto-throttle = 0.5 | 10 | 15 | 45 | etc.")
		print("RETRIES")
		print("    Number of retries per URL")
		print("    Default: 2")
		print("    -r, --retries = 0 | 4 | etc.")
		print("REQUEST TIMEOUT")
		print("    Request timeout in seconds")
		print("    Default: 60")
		print("    -rt, --request-timeout = 30 | 90 | etc.")
		print("USER AGENTS")
		print("    User agents to use")
		print("    Default: random-all")
		print("    -a, --user-agents = user_agents.txt | random(-all) | curl/3.30.1 | etc.")
		print("PROXY")
		print("    Web proxy to use")
		print("    -x, --proxy = http://127.0.0.1:8080 | etc.")
		print("OUT")
		print("    Output file")
		print("    -o, --out = report.json | etc.")
		print("VERBOSE")
		print(f"    Create additional supporting output files that end with '{config.REPORT_EXTENSION}'")
		print("    -v, --verbose")
		print("DEBUG")
		print("    Enable debug output")
		print("    -dbg, --debug")

	def error(self, message):
		if len(sys.argv) > 1:
			print("Missing a mandatory option (-t, -res, -o) and/or optional (-pt, -e, -p, -pw, -cr, -crd, -s, -rs, -at, -r, -rt, -a, -x, -v, -dbg)")
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
		self.__parser.add_argument("-t"  , "--template"                  , required = True , type   = str         , default = ""   )
		self.__parser.add_argument("-res", "--results"                   , required = True , type   = str         , default = ""   )
		self.__parser.add_argument("-pt" , "--plaintext"                 , required = False, action = "store_true", default = False)
		self.__parser.add_argument("-e"  , "--excludes"                  , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-p"  , "--playwright"                , required = False, action = "store_true", default = False)
		self.__parser.add_argument("-pw" , "--playwright-wait"           , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-cr" , "--concurrent-requests"       , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-crd", "--concurrent-requests-domain", required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-s"  , "--sleep"                     , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-rs" , "--random-sleep"              , required = False, action = "store_true", default = False)
		self.__parser.add_argument("-at" , "--auto-throttle"             , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-r"  , "--retries"                   , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-rt" , "--request-timeout"           , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-a"  , "--user-agents"               , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-x"  , "--proxy"                     , required = False, type   = str         , default = ""   )
		self.__parser.add_argument("-o"  , "--out"                       , required = True , type   = str         , default = ""   )
		self.__parser.add_argument("-v"  , "--verbose"                   , required = False, action = "store_true", default = False)
		self.__parser.add_argument("-dbg", "--debug"                     , required = False, action = "store_true", default = False)

	def validate_args(self):
		"""
		Validate and return the CLI arguments.
		"""
		self.__success = True
		self.__args = self.__parser.parse_args()
		self.__validate_template()
		self.__validate_results()
		self.__validate_excludes()
		self.__validate_playwright_wait()
		self.__validate_concurrent_requests()
		self.__validate_concurrent_requests_domain()
		self.__validate_sleep()
		self.__validate_auto_throttle()
		self.__validate_retries()
		self.__validate_request_timeout()
		self.__validate_user_agents()
		self.__validate_proxy()
		return self.__success, self.__args

	def __error(self, message: str):
		"""
		Set the success flag to 'False' to prevent the main task from executing, and print an error message.
		"""
		self.__success = False
		general.print_error(message)

	# ------------------------------------

	def __validate_template(self):
		tmp = None
		if not file.is_file(self.__args.template):
			self.__error(f"\"{self.__args.template}\" does not exist")
		else:
			success, message = file.validate(self.__args.template)
			if not success:
				self.__error(message)
			else:
				tmp = file.read(self.__args.template)
				if not tmp:
					self.__error(f"No template was found in \"{self.__args.template}\"")
				else:
					tmp, message = template.deserialize(tmp)
					if message:
						self.__error(f"{message} from \"{self.__args.template}\"")
		self.__args.template = tmp

	def __validate_results(self):
		tmp = []
		if not directory.exists(self.__args.results):
			self.__error(f"\"{self.__args.results}\" does not exist")
		elif directory.is_directory(self.__args.results):
			success, message = directory.validate(self.__args.results)
			if not success:
				self.__error(message)
			else:
				for path in directory.list_files(self.__args.results):
					if not path.endswith(config.REPORT_EXTENSION):
						tmp.append(path)
				if not tmp:
					self.__error(f"No valid files were found in \"{self.__args.results}\"")
		else:
			success, message = file.validate(self.__args.results)
			if not success:
				self.__error(message)
			else:
				tmp = [self.__args.results]
		self.__args.results = tmp

	def __validate_excludes(self):
		tmp = []
		if self.__args.excludes:
			if file.is_file(self.__args.excludes):
				success, message = file.validate(self.__args.excludes)
				if not success:
					self.__error(message)
				else:
					tmp = file.read_array(self.__args.excludes)
					if not tmp:
						self.__error(f"No regular expressions were found in \"{self.__args.excludes}\"")
					else:
						success, message = grep.validate_multiple(tmp)
						if not success:
							self.__error(message)
			else:
				success, message = grep.validate(self.__args.excludes)
				if not success:
					self.__error(message)
				else:
					tmp = [self.__args.excludes]
		self.__args.excludes = tmp

	def __validate_playwright_wait(self):
		tmp = 0
		if self.__args.playwright_wait:
			tmp = general.to_float(self.__args.playwright_wait)
			if tmp is None:
				self.__error("Playwright's wait time must be numeric")
			elif tmp <= 0:
				self.__error("Playwright's wait time must be greater than zero")
		self.__args.playwright_wait = tmp

	def __validate_concurrent_requests(self):
		tmp = 15
		if self.__args.concurrent_requests:
			if not self.__args.concurrent_requests.isdigit():
				self.__error("Number of concurrent requests must be numeric")
			else:
				tmp = int(self.__args.concurrent_requests)
				if tmp <= 0:
					self.__error("Number of concurrent requests must be greater than zero")
		self.__args.concurrent_requests = tmp

	def __validate_concurrent_requests_domain(self):
		tmp = 5
		if self.__args.concurrent_requests_domain:
			if not self.__args.concurrent_requests_domain.isdigit():
				self.__error("Number of concurrent requests per domain must be numeric")
			else:
				tmp = int(self.__args.concurrent_requests_domain)
				if tmp <= 0:
					self.__error("Number of concurrent requests per domain must be greater than zero")
		self.__args.concurrent_requests_domain = tmp

	def __validate_sleep(self,):
		tmp = 0
		if self.__args.sleep:
			tmp = general.to_float(self.__args.sleep)
			if tmp is None:
				self.__error("Sleep time between two consecutive requests must be numeric")
			elif tmp <= 0:
				self.__error("Sleep time between two consecutive requests must be greater than zero")
		self.__args.sleep = tmp

	def __validate_auto_throttle(self):
		tmp = 0
		if self.__args.auto_throttle:
			tmp = general.to_float(self.__args.auto_throttle)
			if tmp is None:
				self.__error("Auto throttle must be numeric")
			elif tmp <= 0:
				self.__error("Auto throttle must be greater than zero")
		self.__args.auto_throttle = tmp

	def __validate_retries(self):
		tmp = 2
		if self.__args.retries:
			if not self.__args.retries.isdigit():
				self.__error("Number of retries must be numeric")
			else:
				tmp = int(self.__args.retries)
				if tmp <= 0:
					self.__error("Number of retries must be greater than zero")
		self.__args.retries = tmp

	def __validate_request_timeout(self):
		tmp = 60
		if self.__args.request_timeout:
			tmp = general.to_float(self.__args.request_timeout)
			if tmp is None:
				self.__error("Request timeout must be numeric")
			elif tmp <= 0:
				self.__error("Request timeout must be greater than zero")
		self.__args.request_timeout = tmp

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

	def __validate_proxy(self):
		if self.__args.proxy:
			success, message = url.validate(self.__args.proxy)
			if not success:
				self.__error(message)
