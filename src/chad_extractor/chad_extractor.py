#!/usr/bin/env python3

import argparse, asyncio, collections, colorama, copy, datetime, json, multiprocessing, multiprocessing.managers, os, random, regex as re, scrapy, scrapy.crawler, scrapy.utils.project, sys, termcolor, urllib.parse
from   playwright.async_api     import TimeoutError as PlaywrightTimeoutError
from   playwright._impl._errors import Error        as PlaywrightError
from   nagooglesearch           import nagooglesearch

colorama.init(autoreset = True)

# ----------------------------------------

class Stopwatch:

	def __init__(self):
		self.__start = datetime.datetime.now()
		self.__end   = None

	def stop(self):
		self.__end = datetime.datetime.now()
		print(f"Script has finished in {self.__end - self.__start}")

	def get_start(self):
		return self.__start

	def get_end(self):
		return self.__end

stopwatch = Stopwatch()

# ----------------------------------------

KEYS = {
	"extract": {
		"regex"  : "extract",
		"prepend": "extract_prepend",
		"append" : "extract_append",
		"success": "extracted",
		"error"  : "extraction"
	},
	"validate": {
		"regex"          : "validate",
		"cookies"        : "validate_cookies",
		"playwright"     : "validate_browser",
		"playwright_wait": "validate_browser_wait",
		"success"        : "validated",
		"error"          : "validation"
	}
}

IGNORE_HTTPS_ERRORS = True
MAX_REDIRECTS       = 10
DEFAULT_ENCODING    = "ISO-8859-1"
REPORT_EXTENSION    = ".report.json"

# ----------------------------------------

def parse_float(value):
	tmp = None
	try:
		tmp = float(value)
	except ValueError:
		pass
	return tmp

def unique(sequence, sort = False):
	seen = set()
	array = [x for x in sequence if not (x in seen or seen.add(x))]
	if sort and array:
		array = sorted(array, key = str.casefold)
	return array

def get_directory_files(directory): # non-recursive
	tmp = []
	for file in os.listdir(directory):
		file = os.path.join(directory, file)
		if os.path.isfile(file) and os.access(file, os.R_OK) and os.stat(file).st_size > 0:
			tmp.append(file)
	return tmp

def read_file(file, sort = False, array = False):
	return __read_file_array(file, sort) if array else __read_file_text(file)

def __read_file_array(file, sort = False):
	tmp = []
	with open(file, "r", encoding = DEFAULT_ENCODING) as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	return unique(tmp, sort)

def __read_file_text(file):
	return open(file, "r", encoding = DEFAULT_ENCODING).read()

def write_file(data, out):
	confirm = "yes"
	if os.path.isfile(out):
		print(f"'{out}' already exists")
		confirm = input("Overwrite the output file (yes): ")
	if confirm.lower() == "yes":
		try:
			open(out, "w").write(data)
			print(f"Results have been saved to '{out}'")
		except FileNotFoundError:
			print(f"Cannot save results to '{out}'")

def write_file_silent(data, out): # used to create additional supporting output files
	try:
		open(out, "w").write(data)
	except FileNotFoundError:
		pass

def jload_file(file):
	tmp = []
	try:
		tmp = json.loads(read_file(file))
	except json.decoder.JSONDecodeError:
		pass
	return tmp

def jdump(data):
	return json.dumps(data, indent = 4, ensure_ascii = False) if data else ""

def decode(data): # (decoded, error)
	try:
		return (data.decode(DEFAULT_ENCODING), "")
	except UnicodeDecodeError as ex:
		return ("", ex)

def get_timestamp(text):
	print(f"{datetime.datetime.now().strftime('%H:%M:%S')} - {text}")

# ----------------------------------------

def __select(obj, key, sort = False):
	tmp = []
	for entry in obj:
		tmp.append(entry[key])
	return unique(tmp, sort)

def __select_array(obj, key, sort = False):
	tmp = []
	for entry in obj:
		tmp.extend(entry[key])
	return unique(tmp, sort)

def __sort_by(obj, key):
	return sorted(obj, key = lambda entry: entry[key].casefold())

def __group_by_url(obj, sort = False):
	grouped = collections.defaultdict(lambda: {"files": []})
	for entry in obj:
		grouped[entry["url"]]["url"] = entry["url"]
		if "key" in entry:
			grouped[entry["url"]]["key"] = entry["key"]
		grouped[entry["url"]]["files"].append(entry["file"])
	tmp = []
	for entry in list(grouped.values()):
		entry["files"] = unique(entry["files"], sort)
		tmp.append(entry)
	return tmp

def __delete(obj, key):
	tmp = []
	for entry in copy.deepcopy(obj):
		entry.pop(key)
		tmp.append(entry)
	return tmp

def __select_results_array(obj, sort = False):
	tmp = []
	for entry in obj:
		for key in entry["results"]:
			tmp.extend(entry["results"][key])
	return unique(tmp, sort)

def __select_by_file(obj, file):
	tmp = []
	for entry in obj:
		if file in entry["file"]:
			tmp.append(entry)
	return tmp

def __select_url_by_file(obj, file, sort = False):
	tmp = []
	for entry in obj:
		if file in entry["files"]:
			tmp.append(entry["url"])
	return tmp

def __select_by_file_and_delete_files(obj, file, sort = False):
	tmp = []
	for entry in copy.deepcopy(obj):
		if file in entry["files"]:
			entry.pop("files")
			tmp.append(entry)
	return tmp

def jquery(obj, query, value = None, sort = False):
	if query == "select_url":
		return __select(obj, "url", sort)
	elif query == "select_urls":
		return __select_array(obj, "urls", sort)
	elif query == "sort_by_url":
		return __sort_by(obj, "url")
	elif query == "group_by_url":
		return __group_by_url(obj, sort)
	elif query == "select_file":
		return __select(obj, "file", sort)
	elif query == "select_files":
		return __select_array(obj, "files", sort)
	elif query == "sort_by_file":
		return __sort_by(obj, "file")
	elif query == "delete_files":
		return __delete(obj, "files")
	elif query == "select_results":
		return __select_results_array(obj, sort)
	elif query == "select_by_file":
		return __select_by_file(obj, value)
	elif query == "select_by_file_and_delete_files":
		return __select_by_file_and_delete_files(obj, value, sort)
	elif query == "select_url_by_file":
		return __select_url_by_file(obj, value, sort)

# ----------------------------------------

class CustomManager(multiprocessing.managers.BaseManager):
	pass

class SharedStorage:

	def __init__(self, template, data, plaintext, excludes, debug):
		self.__template  = template
		self.__data      = data
		self.__plaintext = plaintext
		self.__excludes  = excludes
		self.__debug     = debug
		# --------------------------------
		self.__extraction = True
		self.__active     = KEYS["extract"]
		# --------------------------------
		self.__flags   = re.MULTILINE | re.IGNORECASE
		self.__results = {
			KEYS["extract" ]["success"]: [],
			KEYS["extract" ]["error"  ]: [],
			KEYS["validate"]["success"]: [],
			KEYS["validate"]["error"  ]: []
		}

	def start_validation(self):
		self.__extraction = False
		self.__active     = KEYS["validate"]

	def validation_started(self):
		return not self.__extraction

	def get_data(self):
		return self.__data

	def has_data(self):
		return bool(self.get_data())

	def get_success(self):
		return self.__results[self.__active["success"]]

	def has_success(self):
		return bool(self.get_success())

	def append_success(self, entry):
		self.__results[self.__active["success"]].append(entry)

	def append_error(self, entry):
		self.__results[self.__active["error"]].append(entry)

	def get_results(self):
		return self.__results

	# 1st round: extraction - pop all entries with no "extract" RegEx
	# 2nd round: validation - pop all entries with no "validate" RegEx
	def parse_template(self):
		for key in list(self.__template.keys()):
			if self.__active["regex"] not in self.__template[key]:
				self.__template.pop(key)
		return bool(self.__template)

	def parse_data(self):
		tmp = []
		if self.__extraction:
			if not self.__plaintext:
				for file in self.__data:
					for url in jquery(jload_file(file), "select_urls"):
						tmp.append(self.input(url, None, file))
			else:
				for file in self.__data:
					results = self.parse_response(response = read_file(file)) # plaintext files are treated like server responses
					if results:
						self.append_success(self.output_plaintext(file, results))
				return self.has_success()
		else:
			if not self.__plaintext:
				for entry in self.__results[KEYS["extract"]["success"]]: # extraction data
					for key in entry["results"]:
						if key in self.__template:
							for url in entry["results"][key]:
								for file in entry["files"]:
									tmp.append(self.input(url, key, file))
			else:
				for entry in self.__results[KEYS["extract"]["success"]]: # extraction data
					for key in entry["results"]:
						if key in self.__template:
							for url in entry["results"][key]:
								tmp.append(self.input(url, key, entry["file"]))
		self.__data = jquery(tmp, "group_by_url")
		return self.has_data()

	def input(self, url, key, file):
		return {"url": url, "key": key, "file": file}

	def output_plaintext(self, file, results):
		return {"file": file, "results": results}

	def output(self, url, results, files):
		return {"url": url, "results": results, "files": files}

	def parse_response(self, response, key = None): # "key" is required only for validation
		tmp = {}
		try:
			if self.__extraction:
				if self.__excludes:
					for exclude in self.__excludes:
						response = re.sub(exclude, "", response, flags = self.__flags)
				for key in self.__template:
					matches = re.findall(self.__template[key][KEYS["extract"]["regex"]], response, flags = self.__flags)
					if matches:
						tmp[key] = self.__concat(key, matches)
			elif key and re.search(self.__template[key][KEYS["validate"]["regex"]], response, flags = self.__flags):
				tmp = True
		except (re.error, KeyError) as ex:
			self.__print_error(ex)
		return tmp

	def __print_error(self, msg):
		if self.__debug:
			termcolor.cprint(msg, "red")

	# ------------------------------------

	def __concat(self, key, matches): # applies only for extraction
		prepend = ""
		if KEYS["extract"]["prepend"] in self.__template[key]:
			prepend = self.__template[key][KEYS["extract"]["prepend"]]
		# --------------------------------
		append = ""
		if KEYS["extract"]["append"] in self.__template[key]:
			append = self.__template[key][KEYS["extract"]["append"]]
		# --------------------------------
		if prepend or append:
			for i in range(len(matches)):
				matches[i] = ("{0}{1}{2}").format(prepend, matches[i], append)
		# --------------------------------
		return unique(matches, sort = True)

	def get_cookies(self, key): # applies only for validation
		cookies = {}
		# --------------------------------
		if KEYS["validate"]["cookies"] in self.__template[key]:
			cookies = self.__template[key][KEYS["validate"]["cookies"]]
		# --------------------------------
		return cookies

	def require_playwright(self): # applies only for validation
		(playwright, playwright_wait) = (False, 0)
		# --------------------------------
		for key in self.__template:
			if KEYS["validate"]["playwright"] in self.__template[key]:
				playwright = True
				break
		# --------------------------------
		return (playwright, playwright_wait)

	def get_playwright(self, key): # applies only for validation
		(playwright, playwright_wait) = (False, 0)
		# --------------------------------
		if KEYS["validate"]["playwright"] in self.__template[key]:
			playwright = self.__template[key][KEYS["validate"]["playwright"]]
		# --------------------------------
		if KEYS["validate"]["playwright_wait"] in self.__template[key]:
			playwright_wait = self.__template[key][KEYS["validate"]["playwright_wait"]]
		# --------------------------------
		return (playwright, playwright_wait)

# ----------------------------------------

def save_results(results, out, verbose, plaintext = False):
	extracted         = KEYS["extract" ]["success"]
	extraction_errors = KEYS["extract" ]["error"  ]
	validated         = KEYS["validate"]["success"]
	validation_errors = KEYS["validate"]["error"  ]
	# ------------------------------------
	tmp = __get_report(plaintext, primary = True)
	# ------------------------------------
	# primary report - extracted
	results[extracted]        = jquery(results[extracted], "sort_by_file" if plaintext else "sort_by_url")
	tmp["full"   ]            = results[extracted] if plaintext else jquery(results[extracted], "delete_files")
	tmp["summary"][extracted] = unique(jquery(tmp["full"], "select_results"), sort = True)
	# ------------------------------------
	# primary report - extraction errors
	# in the plaintext mode, no extraction requests are sent because plaintext files are treated like server responses
	if not plaintext:
		results[extraction_errors]       = jquery(results[extraction_errors], "sort_by_url")
		tmp["failed"][extraction_errors] = jquery(results[extraction_errors], "select_url")
	# ------------------------------------
	# primary report - validated
	results[validated]        = jquery(results[validated], "sort_by_url")
	tmp["summary"][validated] = jquery(results[validated], "select_url")
	# ------------------------------------
	# primary report - validation errors
	results[validation_errors]       = jquery(results[validation_errors], "sort_by_url")
	tmp["failed"][validation_errors] = jquery(results[validation_errors], "select_url")
	# ------------------------------------
	# primary report - write
	write_file(jdump(tmp), out)
	# ------------------------------------
	if verbose:
		for file in jquery(results[extracted], "select_file" if plaintext else "select_files"):
			# ----------------------------
			tmp = __get_report(plaintext, primary = False)
			# ----------------------------
			# secondary report - extracted
			if not plaintext:
				tmp["full"   ]            = jquery(results[extracted], "select_by_file_and_delete_files", file)
				tmp["summary"][extracted] = jquery(tmp["full"], "select_results", sort = True)
			else:
				dump                      = jquery(results[extracted], "select_by_file", file)
				tmp["summary"][extracted] = jquery(dump, "select_results", sort = True)
				tmp["results"]            = dump[0]["results"]
			# ----------------------------
			# secondary report - extraction errors
			# in the plaintext mode, no extraction requests are sent because plaintext files are treated like server responses
			if not plaintext:
				tmp["failed"][extraction_errors] = jquery(results[extraction_errors], "select_url_by_file", file)
			# ----------------------------
			# secondary report - validated
			tmp["summary"][validated] = jquery(results[validated], "select_url_by_file", file)
			# ----------------------------
			# secondary report - validation errors
			tmp["failed"][validation_errors] = jquery(results[validation_errors], "select_url_by_file", file)
			# ----------------------------
			# secondary report - write
			write_file_silent(jdump(tmp), file.rsplit(".", 1)[0] + REPORT_EXTENSION)

def __get_report(plaintext = False, primary = True):
	extracted         = KEYS["extract" ]["success"]
	extraction_errors = KEYS["extract" ]["error"  ]
	validated         = KEYS["validate"]["success"]
	validation_errors = KEYS["validate"]["error"  ]
	# ------------------------------------
	datetime_format   = "%Y-%m-%d %H:%M:%S"
	# ------------------------------------
	tmp = {
		"started_at": stopwatch.get_start().strftime(datetime_format),
		"ended_at"  : stopwatch.get_end().strftime(datetime_format),
		"summary"   : {validated: [], extracted: []},
		"failed"    : {validation_errors: []},
		"full"      : {}
	}
	if not plaintext:
		tmp["failed"][extraction_errors] = []
	elif not primary:
		tmp.pop("full")
		tmp["results"] = {}
	return tmp

# ----------------------------------------

class ChadExtractorSpider(scrapy.Spider):

	name = "ChadExtractorSpider"
	handle_httpstatus_list = [401, 403, 404]

	def __init__(self, shared_storage, playwright, playwright_wait, request_timeout, user_agents, proxy, debug):
		self.__shared_storage  = shared_storage
		self.__validation      = self.__shared_storage.validation_started()
		self.__playwright      = playwright
		self.__playwright_wait = playwright_wait
		self.__request_timeout = request_timeout
		self.__user_agents     = user_agents
		self.__user_agents_len = len(self.__user_agents)
		self.__proxy           = proxy
		self.__debug           = debug
		self.__context         = 0

	# main
	def start_requests(self):
		data = self.__shared_storage.get_data()
		action = KEYS["validate"]["regex"] if self.__shared_storage.validation_started() else KEYS["extract"]["regex"]
		get_timestamp(f"Number of URLs to {action}: {len(data)}")
		print("Press CTRL + C to exit early - results will be saved but please be patient")
		random.shuffle(data) # randomize URLs
		for record in data:
			cookies = {}
			if self.__validation:
				cookies = self.__shared_storage.get_cookies(record["key"])
			yield scrapy.Request(
				url         = record["url"],
				headers     = self.__get_headers(),
				cookies     = cookies,
				meta        = self.__get_meta(record),
				errback     = self.__exception,
				callback    = self.__parse,
				dont_filter = False # if "True", allow duplicate requests
			)

	def __get_headers(self, cookies = None):
		tmp = {
			"User-Agent"               : self.__get_user_agent(),
			"Accept-Language"          : "en-US, *", # some websites require "en-US"
			"Accept"                   : "*/*",
			"Connection"               : "keep-alive",
			"Referer"                  : "https://www.google.com/",
			"Upgrade-Insecure-Requests": "1"
		}
		if cookies:
			tmp["Cookie"] = ("; ").join([f"{key}={value}" for key, value in cookies.items()])
		return tmp

	def __get_user_agent(self):
		return self.__user_agents[random.randint(0, self.__user_agents_len - 1)]

	def __get_meta(self, record):
		# --------------------------------
		(playwright, playwright_wait) = (self.__playwright, self.__playwright_wait)
		if self.__validation and self.__playwright:
			(playwright, playwright_wait) = self.__shared_storage.get_playwright(record["key"])
		# --------------------------------
		self.__context += 1
		return {
			"record"                     : record,          # custom attribute
			"playwright_wait"            : playwright_wait, # custom attribute
			"playwright"                 : playwright,
			"playwright_context"         : str(self.__context),
			"playwright_context_kwargs"  : {
				"ignore_https_errors"    : IGNORE_HTTPS_ERRORS,
				"java_script_enabled"    : True,
				"accept_downloads"       : False,
				"bypass_csp"             : False
			},
			"playwright_include_page"    : playwright,
			"playwright_page_goto_kwargs": {"wait_until": "load"},
			"proxy"                      : self.__proxy,
			"cookiejar"                  : self.__context,
			"dont_merge_cookies"         : False
		}

	# ------------------------------------

	async def __exception(self, failure):
		record     = failure.request.meta["record"    ]
		playwright = failure.request.meta["playwright"]
		status     = 0
		error      = str(failure.value).splitlines()[0]
		if failure.check(scrapy.spidermiddlewares.httperror.HttpError):
			status = failure.value.response.status
		if playwright:
			page = failure.request.meta["playwright_page"]
			if any(entry in error for entry in ["net::ERR_ABORTED", "net::ERR_CONNECTION_RESET"]):
				self.__print_fallback(playwright, status, record["url"])
				error = await self.__playwright_fallback(record, playwright, page)
			await page.close()
			await page.context.close()
		if error:
			self.__parse_error(record, playwright, status, error)

	async def __playwright_fallback(self, record, playwright, page):
		error    = ""
		response = ""
		try:
			cookies  = self.__shared_storage.get_cookies(record["key"])
			response = await page.request.get(
				url                 = record["url"],
				headers             = self.__get_headers(cookies),
				ignore_https_errors = IGNORE_HTTPS_ERRORS,
				timeout             = self.__request_timeout * 1000,
				max_retries         = 0,
				max_redirects       = MAX_REDIRECTS
			)
			body = await response.body() # raw
			body = body.decode(DEFAULT_ENCODING)
			self.__parse_success(record, playwright, response.status, body)
		except (PlaywrightError, PlaywrightTimeoutError, UnicodeDecodeError) as ex:
			error = str(ex).splitlines()[0]
		finally:
			if response:
				await response.dispose()
		return error

	def __parse_error(self, record, playwright, status, error):
		entry = self.__shared_storage.output(record["url"], None, record["files"])
		self.__shared_storage.append_error(entry)
		self.__print_error(playwright, status, record["url"], error)

	def __print_error(self, playwright, status, url, error):
		if self.__debug:
			if status:
				url = f"{status} {url}"
			termcolor.cprint(f"[ ERROR ] PW:{int(playwright)} | {url} -> {error}", "red")

	def __print_fallback(self, playwright, status, url):
		if self.__debug:
			if status:
				url = f"{status} {url}"
			termcolor.cprint(f"[ FALLBACK ] PW:{int(playwright)} | {url} -> Page.goto() -> APIRequestContext.get()", "cyan")

	# ------------------------------------

	async def __parse(self, response):
		record     = response.request.meta["record"    ]
		playwright = response.request.meta["playwright"]
		body       = ""
		error      = ""
		if playwright:
			page = response.request.meta["playwright_page"]
			wait = response.request.meta["playwright_wait"]
			if wait > 0:
				await asyncio.sleep(wait)
			body = await page.content() # text, from Playwright
			await page.close()
			await page.context.close()
		else:
			if hasattr(response, "text"):
				body = response.text
			else:
				(body, error) = decode(response.body) # raw, from Scrapy
		self.__print_redirected(playwright, response.status, record["url"], response.url)
		if error:
			self.__print_error(playwright, response.status, record["url"], error)
		else:
			self.__parse_success(record, playwright, response.status, body)

	def __parse_success(self, record, playwright, status, body):
		entry = self.__shared_storage.output(record["url"], None, record["files"])
		entry["results"] = self.__shared_storage.parse_response(body, record["key"])
		if entry["results"]:
			self.__shared_storage.append_success(entry)
			self.__print_results(playwright, status, record["url"])
		else:
			self.__print_no_results(playwright, status, record["url"])

	def __print_results(self, playwright, status, url):
		if self.__debug:
			termcolor.cprint(f"[ {'VALIDATED' if self.__validation else 'EXTRACTED'} ] PW:{int(playwright)} | {status} {url}", "green")

	def __print_no_results(self, playwright, status, url):
		if self.__debug:
			termcolor.cprint(f"[ NO MATCH ] PW:{int(playwright)} | {status} {url}", "magenta")

	def __print_redirected(self, playwright, status, request_url, response_url):
		if self.__debug and urllib.parse.urlparse(request_url).geturl() != response_url:
			termcolor.cprint(f"[ REDIRECTED ] PW:{int(playwright)} | {request_url} -> {status} {response_url}", "yellow")

# ----------------------------------------

class ChadExtractor:

	def __init__(self, shared_storage, playwright, playwright_wait, concurrent_requests, concurrent_requests_domain, sleep, random_sleep, auto_throttle, retries, request_timeout, user_agents, proxy, debug):
		self.__shared_storage             = shared_storage
		self.__playwright                 = playwright
		self.__playwright_wait            = playwright_wait
		self.__concurrent_requests        = concurrent_requests
		self.__concurrent_requests_domain = concurrent_requests_domain
		self.__sleep                      = sleep
		self.__random_sleep               = random_sleep
		self.__auto_throttle              = auto_throttle
		self.__retries                    = retries
		self.__request_timeout            = request_timeout # all timeouts
		self.__user_agents                = user_agents
		self.__proxy                      = proxy
		self.__debug                      = debug
		# --------------------------------
		self.__headless_browser           = True
		self.__handle_sigint              = False
		self.__browser_type               = "chromium" # Playwright's headless browser

	def __run(self):
		settings = scrapy.utils.project.get_project_settings()
		# --------------------------------
		settings["COOKIES_ENABLED"         ] = True
		settings["DOWNLOAD_TIMEOUT"        ] = self.__request_timeout # connect / read timeout
		settings["DOWNLOAD_DELAY"          ] = self.__sleep
		settings["RANDOMIZE_DOWNLOAD_DELAY"] = self.__random_sleep
		settings["HTTPPROXY_ENABLED"       ] = bool(self.__proxy)
		# --------------------------------
		settings["EXTENSIONS"]["scrapy.extensions.throttle.AutoThrottle"] = 100
		# --------------------------------
		settings["AUTOTHROTTLE_ENABLED"           ] = self.__auto_throttle > 0
		settings["AUTOTHROTTLE_DEBUG"             ] = False
		settings["AUTOTHROTTLE_START_DELAY"       ] = self.__sleep
		settings["AUTOTHROTTLE_MAX_DELAY"         ] = settings["AUTOTHROTTLE_START_DELAY"] + 30
		settings["AUTOTHROTTLE_TARGET_CONCURRENCY"] = self.__auto_throttle
		# --------------------------------
		settings["CONCURRENT_REQUESTS"           ] = self.__concurrent_requests
		settings["CONCURRENT_REQUESTS_PER_DOMAIN"] = self.__concurrent_requests_domain
		settings["RETRY_ENABLED"                 ] = self.__retries > 0
		settings["RETRY_TIMES"                   ] = self.__retries
		settings["REDIRECT_ENABLED"              ] = MAX_REDIRECTS > 0
		settings["REDIRECT_MAX_TIMES"            ] = MAX_REDIRECTS
		# --------------------------------
		settings["ROBOTSTXT_OBEY"                      ] = False
		settings["TELNETCONSOLE_ENABLED"               ] = False
		settings["LOG_ENABLED"                         ] = False
		settings["REQUEST_FINGERPRINTER_IMPLEMENTATION"] = "2.7"
		# --------------------------------
		if self.__shared_storage.validation_started():
			(self.__playwright, self.__playwright_wait) = self.__shared_storage.require_playwright()
		# --------------------------------
		if self.__playwright:
			settings["DOWNLOAD_HANDLERS"]["https"] = "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler"
			settings["DOWNLOAD_HANDLERS"]["http" ] = "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler"
			settings["TWISTED_REACTOR"           ] = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
			settings["PLAYWRIGHT_LAUNCH_OPTIONS" ] = {
				"headless"     : self.__headless_browser,
				"handle_sigint": self.__handle_sigint,
				"proxy"        : {"server": self.__proxy} if self.__proxy else None
			}
			settings["PLAYWRIGHT_BROWSER_TYPE"              ] = self.__browser_type
			settings["PLAYWRIGHT_ABORT_REQUEST"             ] = self.__page_block
			settings["PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT"] = self.__request_timeout * 1000
		# --------------------------------
		crawler = scrapy.crawler.CrawlerProcess(settings)
		crawler.crawl(ChadExtractorSpider, self.__shared_storage, self.__playwright, self.__playwright_wait, self.__request_timeout, self.__user_agents, self.__proxy, self.__debug)
		crawler.start()
		crawler.join()

	def run(self):
		process = multiprocessing.Process(target = self.__run)
		try:
			process.start()
			process.join()
		except KeyboardInterrupt:
			process.terminate()
			process.join()
		return self.__shared_storage.has_success()

	def __page_block(self, request):
		return request.resource_type in ["fetch", "stylesheet", "image", "ping", "font", "media", "imageset", "beacon", "csp_report", "object", "texttrack", "manifest"]

# ----------------------------------------

class MyArgParser(argparse.ArgumentParser):

	def print_help(self):
		print("Chad Extractor v6.6 ( github.com/ivan-sincek/chad )")
		print("")
		print("Usage:   chad-extractor -t template      -res results      -o out         [-s sleep] [-rs random-sleep]")
		print("Example: chad-extractor -t template.json -res chad_results -o report.json [-s 1.5  ] [-rs             ]")
		print("")
		print("DESCRIPTION")
		print("    Extract and validate data from Chad results or plaintext files")
		print("TEMPLATE")
		print("    Template file with extraction and validation details")
		print("    -t, --template = template.json | etc.")
		print("RESULTS")
		print("    Directory with Chad results or plaintext files, or a single file")
		print(f"    If directory, files ending with '{REPORT_EXTENSION}' will be ignored")
		print("    -res, --results = chad_results | results.json | urls.txt | etc.")
		print("PLAINTEXT")
		print("    Treat all the results as plaintext files")
		print("    -pt, --plaintext")
		print("EXCLUDES")
		print("    File with regular expressions or a single regular expression to exclude the content from the page")
		print("    Applies only for extraction")
		print("    -e, --excludes = regexes.txt | \"<div id=\\\"seo\\\">.+?<\\/div>\" | etc.")
		print("PLAYWRIGHT")
		print("    Use Playwright's headless browser")
		print("    Applies only for extraction")
		print("    For validation, use the template file")
		print("    -p, --playwright")
		print("PLAYWRIGHT WAIT")
		print("    Wait time in seconds before fetching the content from the page")
		print("    Applies only for extraction and if Playwright's headless browser is used")
		print("    For validation, use the template file")
		print("    -pw, --playwright-wait = 2 | 4 | etc.")
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
		print("    Randomize the sleep time on each request to vary between '0.5 * sleep' and '1.5 * sleep'")
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
		print("    -a, --user-agents = curl/3.30.1 | user_agents.txt | random[-all] | etc.")
		print("PROXY")
		print("    Web proxy to use")
		print("    -x, --proxy = http://127.0.0.1:8080 | etc.")
		print("OUT")
		print("    Output file")
		print("    -o, --out = report.json | etc.")
		print("VERBOSE")
		print(f"    Create additional supporting output files that end with '{REPORT_EXTENSION}'")
		print("    -v, --verbose")
		print("DEBUG")
		print("    Debug output")
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
		self.__proceed = True
		self.__parser  = MyArgParser()
		self.__parser.add_argument("-t"  , "--template"                  , required = True , type   = str         , default = ""   )
		self.__parser.add_argument("-pt" , "--plaintext"                 , required = False, action = "store_true", default = False) # needs to be in front of the results
		self.__parser.add_argument("-res", "--results"                   , required = True , type   = str         , default = ""   )
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

	def run(self):
		self.__args                            = self.__parser.parse_args()
		self.__args.template                   = self.__parse_template(self.__args.template)                                     # required
		self.__args.results                    = self.__parse_results(self.__args.results)                                       # required
		self.__args.excludes                   = self.__parse_excludes(self.__args.excludes)                                     if self.__args.excludes                   else []
		self.__args.playwright_wait            = self.__parse_playwright_wait(self.__args.playwright_wait)                       if self.__args.playwright_wait            else 0
		self.__args.concurrent_requests        = self.__parse_concurrent_requests(self.__args.concurrent_requests)               if self.__args.concurrent_requests        else 15
		self.__args.concurrent_requests_domain = self.__parse_concurrent_requests_domain(self.__args.concurrent_requests_domain) if self.__args.concurrent_requests_domain else 5
		self.__args.sleep                      = self.__parse_sleep(self.__args.sleep)                                           if self.__args.sleep                      else 0
		self.__args.auto_throttle              = self.__parse_auto_throttle(self.__args.auto_throttle)                           if self.__args.auto_throttle              else 0
		self.__args.retries                    = self.__parse_retries(self.__args.retries)                                       if self.__args.retries                    else 2
		self.__args.request_timeout            = self.__parse_request_timeout(self.__args.request_timeout)                       if self.__args.request_timeout            else 60
		self.__args.user_agents                = self.__parse_user_agents(self.__args.user_agents)                               if self.__args.user_agents                else nagooglesearch.get_all_user_agents()
		self.__args.proxy                      = self.__parse_proxy(self.__args.proxy)                                           if self.__args.proxy                      else ""
		self.__args                            = vars(self.__args)
		return self.__proceed

	def get_arg(self, key):
		return self.__args[key]

	def __error(self, msg):
		self.__proceed = False
		self.__print_error(msg)

	def __print_error(self, msg):
		print(f"ERROR: {msg}")

	def __validate_template_keys(self, value):
		regex = r"[\w\d\-\_]+"
		for pkey, pvalue in value.items():
			if not isinstance(pkey, str) or not pkey:
				self.__error("Template: All primary keys must be non-empty strings")
				break
			elif not re.search(regex, pkey):
				self.__error(f"Template: All primary keys must match {regex} format")
				break
			elif len(pvalue) < 1:
				self.__error("Template: All primary keys must have at least one sub-key")
				break
			elif KEYS["extract"]["regex"] not in pvalue:
				self.__error(f"Template[{pkey}]: Must contain '{KEYS['extract']['regex']}' sub-key")
				break
			error = False
			for skey, svalue in pvalue.items():
				if skey in [KEYS["extract"]["regex"], KEYS["validate"]["regex"]]:
					if not isinstance(svalue, str) or not svalue:
						self.__error(f"Template[{pkey}][{skey}]: Must be a non-empty string")
						error = True
						break
					else:
						try:
							re.compile(svalue)
						except re.error as ex:
							self.__error(f"Template[{pkey}][{skey}]: Invalid RegEx: {svalue}")
							error = True
							break
				elif skey in [KEYS["extract"]["prepend"], KEYS["extract"]["append"]]:
					if not isinstance(svalue, str):
						self.__error(f"Template[{pkey}][{skey}]: Must be a string")
						error = True
						break
				elif skey in [KEYS["validate"]["cookies"]]:
					if not isinstance(svalue, dict):
						self.__error(f"Template[{pkey}][{skey}]: Must be a dictionary")
						error = True
						break
					else:
						pass
				elif skey in [KEYS["validate"]["playwright"]]:
					if not isinstance(svalue, bool):
						self.__error(f"Template[{pkey}][{skey}]: Must be a boolean")
						error = True
						break
				elif skey in [KEYS["validate"]["playwright_wait"]]:
					if not (isinstance(svalue, float) or isinstance(svalue, int)) or float(svalue) < 0:
						self.__error(f"Template[{pkey}][{skey}]: Must be a float and greater than or equal to zero")
						error = True
						break
				else:
					self.__error(f"Template[{pkey}]: Contains non-supported sub-key: {skey}")
					error = True
					break
			if error:
				break
		return value

	def __parse_template(self, value):
		tmp = {}
		if not os.path.isfile(value):
			self.__error("Template file does not exist")
		elif not os.access(value, os.R_OK):
			self.__error("Template file does not have a read permission")
		elif not os.stat(value).st_size > 0:
			self.__error("Template file is empty")
		else:
			tmp = jload_file(value)
			if not tmp:
				self.__error("Template file does not have the correct structure")
			else:
				tmp = self.__validate_template_keys(tmp)
		return tmp

	def __parse_results(self, value):
		results = "plaintext" if self.__args.plaintext else "Chad results"
		tmp = []
		if not os.path.exists(value):
			self.__error(f"Directory with {results} files, or a single file does not exist")
		elif os.path.isdir(value):
			for file in get_directory_files(value):
				if not file.endswith(REPORT_EXTENSION):
					tmp.append(file)
			if not tmp:
				self.__error(f"No {results} files were found")
		else:
			if not os.access(value, os.R_OK):
				self.__error(f"{results.capitalize()} file does not have a read permission")
			elif not os.stat(value).st_size > 0:
				self.__error(f"{results.capitalize()} file is empty")
			else:
				tmp = [value]
		return tmp

	def __validate_regexes(self, values):
		if not isinstance(values, list):
			values = [values]
		try:
			for value in values:
				re.compile(value)
		except re.error as ex:
			self.__error(f"Excludes: Invalid RegEx: {value}")
		return values

	def __parse_excludes(self, value):
		tmp = []
		if os.path.isfile(value):
			if not os.access(value, os.R_OK):
				self.__error("File with regular expressions does not have a read permission")
			elif not os.stat(value).st_size > 0:
				self.__error("File with regular expressions is empty")
			else:
				tmp = read_file(value, array = True)
				if not tmp:
					self.__error("No regular expressions were found")
				else:
					tmp = self.__validate_regexes(tmp)
		else:
			tmp = self.__validate_regexes(value)
		return tmp

	def __parse_playwright_wait(self, value):
		value = parse_float(value)
		if value is None:
			self.__error("Wait time must be numeric")
		elif value <= 0:
			self.__error("Wait time must be greater than zero")
		return value

	def __parse_concurrent_requests(self, value):
		if not value.isdigit():
			self.__error("Number of concurrent requests must be numeric")
		else:
			value = int(value)
			if value <= 0:
				self.__error("Number of concurrent requests must be greater than zero")
		return value

	def __parse_concurrent_requests_domain(self, value):
		if not value.isdigit():
			self.__error("Number of concurrent requests per domain must be numeric")
		else:
			value = int(value)
			if value <= 0:
				self.__error("Number of concurrent requests per domain must be greater than zero")
		return value

	def __parse_sleep(self, value):
		value = parse_float(value)
		if value is None:
			self.__error("Sleep time must be numeric")
		elif value <= 0:
			self.__error("Sleep time must be greater than zero")
		return value

	def __parse_auto_throttle(self, value):
		value = parse_float(value)
		if value is None:
			self.__error("Auto throttle must be numeric")
		elif value <= 0:
			self.__error("Auto throttle must be greater than zero")
		return value

	def __parse_retries(self, value):
		if not value.isdigit():
			self.__error("Number of retries must be numeric")
		else:
			value = int(value)
			if value < 0:
				self.__error("Number of retries must be greater than or equal to zero")
		return value

	def __parse_request_timeout(self, value):
		value = parse_float(value)
		if value is None:
			self.__error("Request timeout must be numeric")
		elif value <= 0:
			self.__error("Request timeout must be greater than zero")
		return value

	def __parse_user_agents(self, value):
		tmp = []
		if os.path.isfile(value):
			if not os.access(value, os.R_OK):
				self.__error("File with user agents does not have a read permission")
			elif not os.stat(value).st_size > 0:
				self.__error("File with user agents is empty")
			else:
				tmp = read_file(value)
				if not tmp:
					self.__error("No user agents were found")
		else:
			lower = value.lower()
			if lower == "random-all":
				tmp = nagooglesearch.get_all_user_agents()
			elif lower == "random":
				tmp = [nagooglesearch.get_random_user_agent()]
			else:
				tmp = [value]
		return tmp

	def __parse_proxy(self, value):
		tmp = urllib.parse.urlsplit(value)
		if not tmp.scheme:
			self.__error("Proxy URL: Scheme is required")
		elif tmp.scheme not in ["http", "https", "socks4", "socks4h", "socks5", "socks5h"]:
			self.__error("Proxy URL: Supported schemes are 'http[s]', 'socks4[h]', and 'socks5[h]'")
		elif not tmp.netloc:
			self.__error("Proxy URL: Invalid domain name")
		elif tmp.port and (tmp.port < 1 or tmp.port > 65535):
			self.__error("Proxy URL: Port number is out of range")
		return value

# ----------------------------------------

def main():
	validate = Validate()
	if validate.run():
		print("###########################################################################")
		print("#                                                                         #")
		print("#                           Chad Extractor v6.6                           #")
		print("#                                   by Ivan Sincek                        #")
		print("#                                                                         #")
		print("# Extract and validate data from Chad results or plaintext files.         #")
		print("# GitHub repository at github.com/ivan-sincek/chad.                       #")
		print("# Feel free to donate ETH at 0xbc00e800f29524AD8b0968CEBEAD4cD5C5c1f105.  #")
		print("#                                                                         #")
		print("###########################################################################")
		results   = {}
		plaintext = validate.get_arg("plaintext")
		CustomManager.register("SharedStorage", SharedStorage)
		with CustomManager() as manager:
			shared_storage = manager.SharedStorage(
				validate.get_arg("template"),
				validate.get_arg("results"),
				plaintext,
				validate.get_arg("excludes"),
				validate.get_arg("debug")
			)
			chad_extractor = ChadExtractor(
 				shared_storage,
 				validate.get_arg("playwright"),
 				validate.get_arg("playwright_wait"),
 				validate.get_arg("concurrent_requests"),
 				validate.get_arg("concurrent_requests_domain"),
 				validate.get_arg("sleep"),
 				validate.get_arg("random_sleep"),
 				validate.get_arg("auto_throttle"),
 				validate.get_arg("retries"),
 				validate.get_arg("request_timeout"),
 				validate.get_arg("user_agents"),
 				validate.get_arg("proxy"),
 				validate.get_arg("debug")
 			)
			if not shared_storage.parse_template():
				print("No extraction details were found in the template file")
			elif not shared_storage.parse_data():
				print("No data was extracted" if plaintext else "No Chad results are suitable for extraction")
			elif not plaintext and not chad_extractor.run():
				print("No data was extracted")
			else:
				shared_storage.start_validation()
				if not shared_storage.parse_template():
					print("No validation details were found in the template file")
				elif not shared_storage.parse_data():
					print("No extracted data is suitable for validation")
				elif not chad_extractor.run():
					print("No extracted data matched the validation criteria")
				results = shared_storage.get_results()
			stopwatch.stop()
			if results:
				save_results(
					results,
					validate.get_arg("out"),
					validate.get_arg("verbose"),
					plaintext
				)

if __name__ == "__main__":
	main()
