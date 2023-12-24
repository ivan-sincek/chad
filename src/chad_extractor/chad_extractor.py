#!/usr/bin/env python3

import datetime, time, sys, os, json, jq, regex as re, random, threading, concurrent.futures, subprocess, asyncio, signal
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
# from playwright._impl._api_types import Error as PlaywrightError # playwright<1.40.0
from playwright._impl._errors import Error as PlaywrightError
from nagooglesearch import nagooglesearch

start = datetime.datetime.now()

# ----------------------------------------

def check_directory_files(directory):
	tmp = []
	for file in os.listdir(directory):
		file = os.path.join(directory, file)
		if os.path.isfile(file) and os.access(file, os.R_OK) and os.stat(file).st_size > 0:
			tmp.append(file)
	return tmp

def unique(sequence, sort = False):
	seen = set()
	array = [x for x in sequence if not (x in seen or seen.add(x))]
	if sort and array:
		array = sorted(array, key = str.casefold)
	return array

encoding = "ISO-8859-1"

def read_file(file, sort = False, array = True):
	return __read_file_array(file, sort) if array else __read_file_text(file)

def __read_file_array(file, sort = False):
	tmp = []
	with open(file, "r", encoding = encoding) as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	stream.close()
	return unique(tmp, sort)

def __read_file_text(file):
	return open(file, "r", encoding = encoding).read()

def write_file(data, out):
	confirm = "yes"
	if os.path.isfile(out):
		print(("'{0}' already exists").format(out))
		confirm = input("Overwrite the output file (yes): ")
	if confirm.lower() == "yes":
		try:
			open(out, "w").write(data)
			print(("Results have been saved to '{0}'").format(out))
		except FileNotFoundError:
			print(("Cannot save results to '{0}'").format(out))

def write_file_silent(data, out):
	try:
		open(out, "w").write(data)
	except FileNotFoundError:
		pass

def jload_file(file):
	tmp = []
	try:
		tmp = json.loads(read_file(file, array = False))
	except json.decoder.JSONDecodeError:
		pass
	return tmp

def jdump(data):
	return json.dumps(data, indent = 4, ensure_ascii = False) if data else ""

def jquery(obj, query):
	tmp = []
	try:
		tmp = jq.compile(query).input(obj).all()
	except ValueError:
		pass
	return tmp

def get_timestamp(text):
	return print(("{0} - {1}").format(datetime.datetime.now().strftime("%H:%M:%S"), text))

# ----------------------------------------

class ChadExtractor:

	def __init__(
		self,
		template,
		results,
		excludes,
		threads,
		retries,
		wait,
		agents,
		proxy,
		out,
		extension,
		verbose,
		debug
	):
		self.__template       = template
		self.__results        = results
		self.__excludes       = excludes
		self.__threads        = threads
		self.__retries        = retries
		self.__wait           = wait
		self.__start          = 4 # delay between starting each headless browser
		self.__agents         = agents
		self.__proxy          = {"server": proxy} if proxy else None
		self.__out            = out
		self.__extension      = extension
		self.__verbose        = verbose
		self.__debug          = debug
		self.__debug_lock     = threading.Lock()
		# --------------------------------
		self.__keys           = {
			"extract": True,
			"data"   : {
				"extract": {
					"template": "extract",
					"success" : "extracted",
					"failed"  : "failed_extraction",
					"failure" : "extraction",
					"prepend" : "extract_prepend",
					"append"  : "extract_append"
				},
				"validate": {
					"template": "validate",
					"success" : "validated",
					"failed"  : "failed_validation",
					"failure" : "validation",
					"prepend" : "validate_prepend",
					"append"  : "validate_append"
				}
			}
		}
		self.__keys["active"] = self.__keys["data"]["extract"]
		self.__data           = {
			self.__keys["data"]["extract" ]["success"]: [],
			self.__keys["data"]["extract" ]["failed" ]: [],
			self.__keys["data"]["validate"]["success"]: [],
			self.__keys["data"]["validate"]["failed" ]: []
		}
		self.__data_lock      = threading.Lock()
		# --------------------------------
		self.__queries        = {
			"get_url"     : ".[].url",
			"get_urls"    : ".[].urls[]",
			"sort_by_url" : "sort_by(.url | ascii_downcase)[]",
			"group_by_url": "group_by(.url) | map((.[0] | del(.file)) + {files: (map(.file) | unique)})[]",
			"get_file"    : ".[].file",
			"get_files"   : ".[].files[]",
			"sort_by_file": "sort_by(.file | ascii_downcase)[]",
			"delete_files": ".[] | del(.files)",
			"get_results" : ".[].results[][]"
		}
		self.__flags          = re.MULTILINE | re.IGNORECASE
		# --------------------------------
		self.__close          = False

	def set_validate(self):
		self.__keys["extract"] = False
		self.__keys["active" ] = self.__keys["data"]["validate"]

	def __extend_data(self, succeeded, failed):
		with self.__data_lock:
			self.__data[self.__keys["active"]["success"]].extend(succeeded)
			self.__data[self.__keys["active"]["failure"]].extend(failed)

	def parse_template(self):
		tmp = {}
		for key in self.__template:
			if self.__keys["active"]["template"] in self.__template[key]:
				tmp[key] = self.__template[key]
		self.__template = tmp
		return bool(self.__template)

	def parse_input(self, plaintext = False):
		tmp = []
		if self.__keys["extract"]:
			if not plaintext:
				for file in self.__results:
					for url in jquery(jload_file(file), self.__queries["get_urls"]):
						tmp.append({"file": file, "url": url})
			else:
				for file in self.__results:
					results = self.__parse_response(None, read_file(file, array = False)) # plaintext files are treated like server responses
					if results:
						self.__data[self.__keys["data"]["extract"]["success"]].append({"file": file, "results": results})
						for key in results:
							if key in self.__template:
								for url in results[key]:
									tmp.append({"file": file, "url": url, "id": key})
		else:
			for entry in self.__data[self.__keys["data"]["extract"]["success"]]:
				for key in entry["results"]:
					if key in self.__template:
						for url in entry["results"][key]:
							for file in entry["files"]:
								tmp.append({"file": file, "url": url, "id": key})
		self.__results = jquery(tmp, self.__queries["group_by_url"])
		return bool(self.__results)

	def __parse_response(self, record, response):
		tmp = {}
		try:
			if self.__keys["extract"]:
				if self.__excludes:
					for exclude in self.__excludes:
						response = re.sub(exclude, "", response, flags = self.__flags)
				for key in self.__template:
					matches = re.findall(self.__template[key][self.__keys["data"]["extract"]["template"]], response, flags = self.__flags)
					if matches:
						tmp[key] = self.__concat(key, matches)
			elif re.search(self.__template[record["id"]][self.__keys["data"]["validate"]["template"]], response, flags = self.__flags):
				tmp = True
		except (re.error, KeyError) as ex:
			self.__print_ex(ex)
		return tmp

	def __concat(self, key, matches):
		prepend = ""
		if self.__keys["data"]["extract"]["prepend"] in self.__template[key]:
			prepend = self.__template[key][self.__keys["data"]["extract"]["prepend"]]
		append = ""
		if self.__keys["data"]["extract"]["append"] in self.__template[key]:
			append = self.__template[key][self.__keys["data"]["extract"]["append"]]
		if prepend or append:
			for i in range(len(matches)):
				matches[i] = prepend + matches[i] + append
		return unique(matches, sort = True)

	def run(self):
		signal.signal(signal.SIGINT, self.__interrupt)
		self.__close = False
		get_timestamp(("Number of URLs to be {0}: {1}").format(self.__keys["active"]["success"], len(self.__results)))
		print("Press CTRL + C to exit early - results will be saved")
		random.shuffle(self.__results) # anti-bot evasion 1
		with concurrent.futures.ThreadPoolExecutor(max_workers = self.__threads) as executor:
			subprocesses = []
			for records in self.__split_results():
				if subprocesses:
					time.sleep(self.__start)
				subprocesses.append(executor.submit(self.__proxy_browser_requests, records, len(subprocesses) + 1))
			concurrent.futures.wait(subprocesses)
		return bool(self.__data[self.__keys["active"]["success"]])

	def __interrupt(self, signum, frame):
		self.__close = True
		self.__print_msg("Please wait for a clean exit...")

	def __split_results(self):
		if self.__threads > 1:
			k, m = divmod(len(self.__results), self.__threads)
			return list(filter(None, [self.__results[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(self.__threads)]))
		else:
			return [self.__results]

	def __proxy_browser_requests(self, records, identifier):
		if not self.__close:
			self.__print_debug("Starting browser thread", identifier)
			asyncio.run(self.__browser_requests(records))

	async def __browser_requests(self, records):
		succeeded = []
		failed    = []
		pw        = None
		browser   = None
		context   = None
		try:
			pw      = await async_playwright().start()
			browser = await pw.chromium.launch(
				headless      = True,
				handle_sigint = False, # do not terminate the browser on CTRL + C
				proxy         = self.__proxy
			)
			context = await self.__set_context(browser)
			# context.set_default_timeout(60000) # default: 30s
			cache_reset = 0
			cache_limit = 100
			for record in records:
				# playwright issue / bug
				# reusing same context leads to large resource consumption and crash
				cache_reset += 1
				if cache_reset % cache_limit:
					cache_reset = 0
					await context.close()
					context = await self.__set_context(browser)
				entry = {"files": record["files"], "url": record["url"], "results": {}}
				count = self.__retries + 1
				while count > 0 and not self.__close:
					await context.set_extra_http_headers(self.__get_headers()) # anti-bot evasion 2
					# --------------------
					tmp = await self.__page_get(context, record["url"])
					if tmp["error"]:
						tmp = await self.__request_get(context, record["url"])
						if tmp["error"]:
							count = 0
					# --------------------
					if tmp["error"] or not tmp["response"]:
						count -= 1
						if count < 1:
							failed.append(entry)
					else:
						count = 0
						entry["results"] = self.__parse_response(record, tmp["response"])
						if entry["results"]:
							succeeded.append(entry)
					# --------------------
					await context.clear_cookies() # anti-bot evasion 3
				if self.__close:
					break
		except (PlaywrightError, Exception) as ex:
			self.__print_ex(ex)
		finally:
			if context:
				await context.close()
			if browser:
				await browser.close()
			if pw:
				await pw.stop()
		self.__extend_data(succeeded, failed)

	async def __set_context(self, browser):
		return await browser.new_context(
			ignore_https_errors = True,
			java_script_enabled = True,
			accept_downloads    = False,
			bypass_csp          = False
		)

	def __get_headers(self):
		return {
			"Accept": "*/*",
			"Accept-Language": "*",
			"Connection": "keep-alive",
			"Referer": "https://www.google.com/",
			# "Upgrade-Insecure-Requests": "1", # some websites might return incorrect page content because of this request header
			"User-Agent": self.__get_user_agent()
		}

	def __get_user_agent(self):
		return self.__agents[random.randint(0, len(self.__agents) - 1)] if self.__agents else nagooglesearch.get_random_user_agent()

	async def __page_get(self, context, url):
		tmp = {"response": None, "error": False}
		page = None
		try:
			page = await context.new_page()
			await page.route("**/*", self.__block) # block unnecessary requests
			response = await page.goto(url)
			if self.__wait:
				await asyncio.sleep(self.__wait)
			await page.wait_for_load_state(state = "load")
			try:
				await page.wait_for_load_state(state = "networkidle") # wait until network is idle for 500ms within 30s
			except PlaywrightTimeoutError: # live streams will always timeout
				pass
			tmp["response"] = await page.content()
			self.__print_debug(response.status, url)
		except PlaywrightTimeoutError:
			pass
		except (PlaywrightError, Exception) as ex: # break and fallback in case of request timeout, invalid domain, or file download
			tmp["error"] = True
			self.__print_ex(ex)
		finally:
			if page:
				await page.close()
		return tmp

	async def __block(self, route):
		if route.request.resource_type in ["fetch", "stylesheet", "image", "ping", "font", "media", "imageset", "beacon", "csp_report", "object", "texttrack", "manifest"]:
			await route.abort()
		else:
			await route.continue_()

	async def __request_get(self, context, url):
		tmp = {"response": None, "error": False}
		try:
			response = await context.request.get(url)
			body = await response.body()
			tmp["response"] = body.decode(encoding)
			self.__print_debug(response.status, url)
		except PlaywrightTimeoutError:
			pass
		except (PlaywrightError, Exception) as ex: # break in case of request timeout or invalid domain
			tmp["error"] = True
			self.__print_ex(ex)
		return tmp

	def __print_debug(self, key, value):
		if self.__debug:
			with self.__debug_lock:
				print(("{0}: {1}").format(key, value))

	def __print_ex(self, ex):
		if self.__debug:
			with self.__debug_lock:
				print(ex)

	def __print_msg(self, msg):
		with self.__debug_lock:
			print(msg)

	def save_results(self, plaintext = False):
		extracted          = self.__keys["data"]["extract" ]["success"]
		failed_extraction  = self.__keys["data"]["extract" ]["failed" ]
		failure_extraction = self.__keys["data"]["extract" ]["failure"]
		validated          = self.__keys["data"]["validate"]["success"]
		failed_validation  = self.__keys["data"]["validate"]["failed" ]
		failure_validation = self.__keys["data"]["validate"]["failure"]
		tmp                = self.__get_report(plaintext)
		# --------------------------------
		self.__data[extracted]    = jquery(self.__data[extracted], self.__queries["sort_by_file" if plaintext else "sort_by_url"])
		tmp["full"   ]            = self.__data[extracted] if plaintext else jquery(self.__data[extracted], self.__queries["delete_files"])
		tmp["summary"][extracted] = unique(jquery(tmp["full"], self.__queries["get_results"]), sort = True)
		# --------------------------------
		if not plaintext:
			self.__data[failed_extraction]    = jquery(self.__data[failed_extraction], self.__queries["sort_by_url"])
			tmp["failed"][failure_extraction] = jquery(self.__data[failed_extraction], self.__queries["get_url"])
		# --------------------------------
		self.__data[validated]    = jquery(self.__data[validated], self.__queries["sort_by_url"])
		tmp["summary"][validated] = jquery(self.__data[validated], self.__queries["get_url"])
		# --------------------------------
		self.__data[failed_validation]    = jquery(self.__data[failed_validation], self.__queries["sort_by_url"])
		tmp["failed"][failure_validation] = jquery(self.__data[failed_validation], self.__queries["get_url"])
		# --------------------------------
		write_file(jdump(tmp), self.__out)
		# --------------------------------
		if self.__verbose:
			for file in unique(jquery(self.__data[extracted], self.__queries["get_file" if plaintext else "get_files"])):
				# ------------------------
				tmp = self.__get_report(plaintext, main = False)
				# ------------------------
				if not plaintext:
					tmp["full"   ]              = jquery(self.__data[extracted], (".[] | select(.files | index(\"{0}\")) | del(.files)").format(file))
					tmp["summary"]["extracted"] = unique(jquery(tmp["full"], self.__queries["get_results"]), sort = True)
				else:
					obj                         = jquery(self.__data[extracted], (".[] | select(.file == \"{0}\") | del(.file)").format(file))
					tmp["summary"]["extracted"] = unique(jquery(obj, self.__queries["get_results"]), sort = True)
					tmp["results"]              = obj[0]["results"]
				# ------------------------
				query = (".[] | select(.files | index(\"{0}\")) | .url").format(file)
				# ------------------------
				if not plaintext:
					tmp["failed"][failure_extraction] = jquery(self.__data[failed_extraction], query)
				# ------------------------
				tmp["summary"][validated] = jquery(self.__data[validated], query)
				# ------------------------
				tmp["failed"][failure_validation] = jquery(self.__data[failed_validation], query)
				# ------------------------
				write_file_silent(jdump(tmp), file.rsplit(".", 1)[0] + self.__extension)
				# ------------------------

	def __get_report(self, plaintext = False, main = True):
		extracted          = self.__keys["data"]["extract" ]["success"]
		failure_extraction = self.__keys["data"]["extract" ]["failure"]
		validated          = self.__keys["data"]["validate"]["success"]
		failure_validation = self.__keys["data"]["validate"]["failure"]
		# --------------------------------
		tmp = {}
		tmp["started_at"] = start.strftime("%Y-%m-%d %H:%M:%S")
		tmp["summary"] = {}
		tmp["summary"][validated] = []
		tmp["summary"][extracted] = []
		tmp["failed"] = {}
		tmp["failed"][failure_validation] = []
		tmp["full"] = {}
		if not plaintext:
			tmp["failed"][failure_extraction] = []
		elif not main:
			tmp["results"] = {}
			tmp.pop("full")
		return tmp

# ----------------------------------------

# my own validation algorithm

class Validate:

	def __init__(self):
		self.__proceed   = True
		self.__extension = ".report.json"
		self.__args      = {
			"template" : None,
			"results"  : None,
			"plaintext": None,
			"excludes" : None,
			"threads"  : None,
			"retries"  : None,
			"wait"     : None,
			"agents"   : None,
			"proxy"    : None,
			"out"      : None,
			"verbose"  : None,
			"debug"    : None
		}

	def __basic(self):
		self.__proceed = False
		print("Chad Extractor v5.1 ( github.com/ivan-sincek/chad )")
		print("")
		print("Usage:   chad-extractor -t template      -res results -o out                 [-th threads] [-r retries] [-w wait] [-a agents         ]")
		print("Example: chad-extractor -t template.json -res results -o results_report.json [-th 10     ] [-r 5      ] [-w 10  ] [-a user_agents.txt]")

	def __advanced(self):
		self.__basic()
		print("")
		print("DESCRIPTION")
		print("    Extract and validate data from Chad results or plaintext files")
		print("TEMPLATE")
		print("    JSON template file with extraction and validation information")
		print("    -t <template> - template.json | etc.")
		print("RESULTS DIRECTORY/FILE")
		print("    Directory containing Chad results or plaintext files, or a single file")
		print("    Files ending with '.report.json' will be ignored")
		print("    -res <results> - results | results.json | urls.txt | etc.")
		print("PLAINTEXT")
		print("    Treat files as plaintext")
		print("    -pt <plaintext> - yes")
		print("EXCLUDES")
		print("    File with regular expressions or a single expression to exclude the page content")
		print("    Applies only on extraction")
		print("    -e <excludes> - regexes.txt | \"<div id=\\\"seo\\\">.+?<\\/div>\" | etc.")
		print("THREADS")
		print("    Number of parallel headless browsers to run")
		print("    Default: 4")
		print("    -th <threads> - 10 | etc.")
		print("RETRIES")
		print("    Number of retries per URL")
		print("    Default: 2")
		print("    -r <retries> - 5 | etc.")
		print("WAIT")
		print("    Wait before returning the page content")
		print("    Default: 4")
		print("    -w <wait> - 10 | etc.")
		print("AGENTS")
		print("    File with user agents to use")
		print("    Default: random")
		print("    -a <agents> - user_agents.txt | etc.")
		print("PROXY")
		print("    Web proxy to use")
		print("    -p <proxy> - http://127.0.0.1:8080 | etc.")
		print("OUT")
		print("    Output file")
		print("    -o <out> - results_report.json | etc.")
		print("VERBOSE")
		print("    Create additional supporting output files")
		print("    -v <verbose> - yes")
		print("DEBUG")
		print("    Debug output")
		print("    -dbg <debug> - yes")

	def __print_error(self, msg):
		print(("ERROR: {0}").format(msg))

	def __error(self, msg, help = False):
		self.__proceed = False
		self.__print_error(msg)
		if help:
			print("Use -h for basic and --help for advanced info")

	def __parse_regexes(self, regexes):
		if not isinstance(regexes, list):
			regexes = [regexes]
		try:
			for regex in regexes:
				re.compile(regex)
		except re.error as ex:
			self.__error("Invalid exclude regular expression was detected")
		return regexes

	def __validate(self, key, value):
		value = value.strip()
		if len(value) > 0:
			# ----------------------------
			if key == "-t" and self.__args["template"] is None:
				self.__args["template"] = value
				if not os.path.isfile(self.__args["template"]):
					self.__error("Template file does not exists")
				elif not os.access(self.__args["template"], os.R_OK):
					self.__error("Template file does not have read permission")
				elif not os.stat(self.__args["template"]).st_size > 0:
					self.__error("Template file is empty")
				else:
					self.__args["template"] = jload_file(self.__args["template"])
					if not self.__args["template"]:
						self.__error("Template file has invalid JSON format")
			# ----------------------------
			elif key == "-res" and self.__args["results"] is None:
				self.__args["results"] = value
				if not os.path.exists(self.__args["results"]):
					self.__error("Directory containing Chad results or plaintext files, or a single file does not exists")
				elif os.path.isdir(self.__args["results"]):
					self.__args["results"] = [file for file in check_directory_files(self.__args["results"]) if not file.endswith(self.__extension)]
					if not self.__args["results"]:
						self.__error("No valid Chad results or plaintext files were found")
				else:
					if not os.access(self.__args["results"], os.R_OK):
						self.__error("Chad results or plaintext file does not have read permission")
					elif not os.stat(self.__args["results"]).st_size > 0:
						self.__error("Chad results or plaintext file is empty")
					else:
						self.__args["results"] = [self.__args["results"]]
			# ----------------------------
			elif key == "-pt" and self.__args["plaintext"] is None:
				self.__args["plaintext"] = value.lower()
				if self.__args["plaintext"] != "yes":
					self.__error("Specify 'yes' to treat files as plaintext")
			# ----------------------------
			elif key == "-e" and self.__args["excludes"] is None:
				self.__args["excludes"] = value
				if os.path.isfile(self.__args["excludes"]):
					if not os.access(self.__args["excludes"], os.R_OK):
						self.__error("File with regular expressions does not have read permission")
					elif not os.stat(self.__args["excludes"]).st_size > 0:
						self.__error("File with regular expressions is empty")
					else:
						self.__args["excludes"] = self.__parse_regexes(read_file(self.__args["excludes"]))
						if not self.__args["excludes"]:
							self.__error("No regular expressions were found")
				else:
					self.__args["excludes"] = self.__parse_regexes(self.__args["excludes"])
			# ----------------------------
			elif key == "-th" and self.__args["threads"] is None:
				self.__args["threads"] = value
				if not self.__args["threads"].isdigit():
					self.__error("Number of parallel headless browsers must be numeric")
				else:
					self.__args["threads"] = int(self.__args["threads"])
					if self.__args["threads"] < 1:
						self.__error("Number of parallel headless browsers must be greater than zero")
			# ----------------------------
			elif key == "-r" and self.__args["retries"] is None:
				self.__args["retries"] = value
				if not self.__args["retries"].isdigit():
					self.__error("Number of retries per URL must be numeric")
				else:
					self.__args["retries"] = int(self.__args["retries"])
					if self.__args["retries"] < 0:
						self.__error("Number of retries per URL must be greater than or equal to zero")
			# ----------------------------
			elif key == "-w" and self.__args["wait"] is None:
				self.__args["wait"] = value
				if not self.__args["wait"].isdigit():
					self.__error("Wait before fetching the page content must be numeric")
				else:
					self.__args["wait"] = int(self.__args["wait"])
					if self.__args["wait"] < 0:
						self.__error("Wait before fetching the page content must be greater than or equal to zero")
			# ----------------------------
			elif key == "-a" and self.__args["agents"] is None:
				self.__args["agents"] = value
				if not os.path.isfile(self.__args["agents"]):
					self.__error("File with user agents does not exists")
				elif not os.access(self.__args["agents"], os.R_OK):
					self.__error("File with user agents does not have read permission")
				elif not os.stat(self.__args["agents"]).st_size > 0:
					self.__error("File with user agents is empty")
				else:
					self.__args["agents"] = read_file(self.__args["agents"])
					if not self.__args["agents"]:
						self.__error("No user agents were found")
			# ----------------------------
			elif key == "-p" and self.__args["proxy"] is None:
				self.__args["proxy"] = value
			# ----------------------------
			elif key == "-o" and self.__args["out"] is None:
				self.__args["out"] = value
			# ----------------------------
			elif key == "-v" and self.__args["verbose"] is None:
				self.__args["verbose"] = value.lower()
				if self.__args["verbose"] != "yes":
					self.__error("Specify 'yes' to enable verbosity")
			# ----------------------------
			elif key == "-dbg" and self.__args["debug"] is None:
				self.__args["debug"] = value.lower()
				if self.__args["debug"] != "yes":
					self.__error("Specify 'yes' to enable debug output")
			# ----------------------------

	def __check(self, argc):
		count = 0
		for key in self.__args:
			if self.__args[key] is not None:
				count += 1
		return argc - count == argc / 2

	def run(self):
		# --------------------------------
		argc = len(sys.argv) - 1
		# --------------------------------
		if argc == 0:
			self.__advanced()
		# --------------------------------
		elif argc == 1:
			if sys.argv[1] == "-h":
				self.__basic()
			elif sys.argv[1] == "--help":
				self.__advanced()
			else:
				self.__error("Incorrect usage", True)
		# --------------------------------
		elif argc % 2 == 0 and argc <= len(self.__args) * 2:
			for i in range(1, argc, 2):
				self.__validate(sys.argv[i], sys.argv[i + 1])
			if None in [self.__args["template"], self.__args["results"], self.__args["out"]] or not self.__check(argc):
				self.__error("Missing a mandatory option (-t, -res, -o) and/or optional (-pt, -e, -th, -r, -w, -a, -p, -v, -dbg)", True)
		# --------------------------------
		else:
			self.__error("Incorrect usage", True)
		# --------------------------------
		if self.__proceed:
			if not self.__args["threads"]:
				self.__args["threads"] = 4
			if not self.__args["retries"]:
				self.__args["retries"] = 2
			if not self.__args["wait"]:
				self.__args["wait"] = 4
		# --------------------------------
		return self.__proceed
		# --------------------------------

	def get_extension(self):
		return self.__extension

	def get_arg(self, key):
		return self.__args[key]

# ----------------------------------------

def main():
	validate = Validate()
	if validate.run():
		print("###########################################################################")
		print("#                                                                         #")
		print("#                           Chad Extractor v5.1                           #")
		print("#                                   by Ivan Sincek                        #")
		print("#                                                                         #")
		print("# Extract and validate data from Chad results.                            #")
		print("# GitHub repository at github.com/ivan-sincek/chad.                       #")
		print("# Feel free to donate ETH at 0xbc00e800f29524AD8b0968CEBEAD4cD5C5c1f105.  #")
		print("#                                                                         #")
		print("###########################################################################")
		chad_extractor = ChadExtractor(
			validate.get_arg("template"),
			validate.get_arg("results"),
			validate.get_arg("excludes"),
			validate.get_arg("threads"),
			validate.get_arg("retries"),
			validate.get_arg("wait"),
			validate.get_arg("agents"),
			validate.get_arg("proxy"),
			validate.get_arg("out"),
			validate.get_extension(),
			validate.get_arg("verbose"),
			validate.get_arg("debug")
		)
		if validate.get_arg("plaintext"):
			if not chad_extractor.parse_template():
				print("No extraction entries were found in the template file")
			elif not chad_extractor.parse_input(plaintext = True):
				print("No data was extracted")
			else:
				chad_extractor.set_validate()
				if not chad_extractor.parse_template():
					print("No validation entries were found in the template file")
				elif not chad_extractor.run():
					print("No data matched the validation criteria")
				chad_extractor.save_results(plaintext = True)
		else:
			if not chad_extractor.parse_template():
				print("No extraction entries were found in the template file")
			elif not chad_extractor.parse_input():
				print("No results for data extraction were found")
			elif not chad_extractor.run():
				print("No data was extracted")
			else:
				chad_extractor.set_validate()
				if not chad_extractor.parse_template():
					print("No validation entries were found in the template file")
				elif not chad_extractor.parse_input():
					print("No results for data validation were found")
				elif not chad_extractor.run():
					print("No data matched the validation criteria")
				chad_extractor.save_results()
		print(("Script has finished in {0}").format(datetime.datetime.now() - start))

if __name__ == "__main__":
	main()
