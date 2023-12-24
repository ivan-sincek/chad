#!/usr/bin/env python3

import datetime, dateutil.relativedelta as relativedelta, time, sys, os, random, json, regex as re, concurrent.futures, subprocess, requests, urllib.parse, colorama, termcolor
from nagooglesearch import nagooglesearch

start = datetime.datetime.now()

colorama.init(autoreset = True)

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# ----------------------------------------

def get_filename(url, directory):
	url = urllib.parse.urlsplit(url)
	base = os.path.join(directory, url.netloc)
	if url.path:
		base = os.path.join(directory, url.path.strip("/").rsplit("/", 1)[-1])
	count = 0
	filename = base
	while os.path.exists(filename):
		count += 1
		filename = ("{0} ({1})").format(base, count)
	return filename

def unique(sequence):
	seen = set()
	return [x for x in sequence if not (x in seen or seen.add(x))]

encoding = "ISO-8859-1"

def read_file(file):
	tmp = []
	with open(file, "r", encoding = encoding) as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	stream.close()
	return unique(tmp)

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
		open(out, "wb").write(data)
	except FileNotFoundError:
		pass

def jdump(data):
	return json.dumps(data, indent = 4, ensure_ascii = False)

def get_timestamp(text, color = None):
	text = ("{0} - {1}").format(datetime.datetime.now().strftime("%H:%M:%S"), text)
	termcolor.cprint(text, color) if color else print(text)

# ----------------------------------------

class Chad:

	def __init__(
		self,
		queries,
		site,
		time,
		total_results,
		page_results,
		minimum_queries,
		maximum_queries,
		minimum_pages,
		maximum_pages,
		agents,
		proxies,
		threads,
		sleep_on_start,
		debug
	):
		self.__queries         = queries
		self.__site            = site
		self.__tbs             = self.__init_tbs(time)
		self.__total_results   = total_results
		self.__page_results    = page_results
		self.__minimum_queries = minimum_queries
		self.__maximum_queries = maximum_queries
		self.__minimum_pages   = minimum_pages
		self.__maximum_pages   = maximum_pages
		self.__agents          = agents
		self.__proxies         = Proxies(proxies)
		self.__threads         = threads
		self.__sleep_on_start  = sleep_on_start
		self.__debug           = debug
		self.__blacklist       = self.__init_blacklist()
		self.__flags           = re.MULTILINE | re.IGNORECASE

	def __init_tbs(self, time):
		tmp = "li:1"
		if time:
			tmp = datetime.datetime.today()
			tmp = nagooglesearch.get_tbs(tmp, tmp - relativedelta.relativedelta(months = time))
		return tmp

	def __init_blacklist(self):
		# exclude security related websites that contain Google Dorks to minimize false positive results
		blacklist = ["kb.cert.org", "exploit-db.com"]
		for entry in ["dork", "hack"]:
			for delimiter in ["", "+", "-", "_", "%20"]:
				blacklist.append("google" + delimiter + entry)
		blacklist = ("(?:{0})").format(("|").join([entry.replace(".", "\\.").replace("/", "\\/") for entry in blacklist]))
		return blacklist

	def check_queries(self):
		return bool(self.__queries)

	def validate_queries(self):
		get_timestamp("Validating Google Dorks...")
		print("Google only allows queries up to 32 words in length separated by space")
		tmp = []
		ignored = []
		for query in self.__queries:
			if self.__site:
				if self.__get_site(query):
					ignored.append(query)
					continue
				query = ("site:{0} ({1})").format(self.__site, query)
			if len(query.split(" ")) > 32:
				ignored.append(query)
				continue
			tmp.append(query)
		if ignored:
			self.__print_ignored(ignored)
		self.__queries = unique(tmp)

	def __get_site(self, query):
		return re.search(r"(?<!in|\-)site\:", query, self.__flags)

	def __print_ignored(self, ignored, color = "cyan"):
		print(("QUERIES IGNORED: {0}").format(len(ignored)))
		for query in ignored:
			termcolor.cprint(query, color) if color else print(query)

	def run(self):
		get_timestamp("Searching Google Dorks...")
		print("Press CTRL + C to exit early - results will be saved")
		results = []
		count = 0
		exit_program = False
		try:
			if not self.__sleep_on_start:
				self.__wait()
			for query in self.__queries:
				count += 1
				entry = {"query": query, "proxy": None, "urls": None}
				parameters = {
					"q"     : entry["query"],
					"tbs"   : self.__tbs,
					"num"   : self.__get_num_pages(),
					"hl"    : "en",
					"filter": "0",
					"safe"  : "images"
				}
				while not exit_program:
					# --------------------
					if self.__proxies.available():
						if self.__proxies.round_robin():
							self.__wait()
						entry["proxy"] = self.__proxies.get_proxy()
					elif count > 1:
						self.__wait()
					# --------------------
					self.__status(count, entry["query"], entry["proxy"])
					client = nagooglesearch.SearchClient(
						tld         = "com",
						parameters  = parameters,
						max_results = self.__total_results,
						user_agent  = self.__get_user_agent(),
						proxy       = entry["proxy"],
						min_sleep   = self.__minimum_pages,
						max_sleep   = self.__maximum_pages,
						verbose     = self.__debug
					)
					entry["urls"] = client.search()
					# --------------------
					remove_proxy = False
					for error in [client.get_rate_limit(), client.get_exception()]:
						if error in entry["urls"]:
							entry["urls"].pop(entry["urls"].index(error))
							termcolor.cprint(error, "yellow")
							if entry["proxy"]:
								remove_proxy = True
							else:
								exit_program = True
					# --------------------
					if entry["urls"]:
						if not self.__get_site(entry["query"]):
							entry["urls"] = self.__check_blacklist(entry["urls"])
						results.append(entry)
					# --------------------
					if remove_proxy:
						self.__proxies.remove_proxy(entry["proxy"])
						if not self.__proxies.available():
							termcolor.cprint("All proxies has been exhausted!", "red")
							exit_program = True
					else:
						break
					# --------------------
				if exit_program:
					break
		except KeyboardInterrupt:
			pass
		return results

	def __wait(self):
		seconds = random.randint(self.__minimum_queries, self.__maximum_queries)
		print(("Sleeping between requests for {0} seconds...").format(seconds))
		time.sleep(seconds)

	def __get_num_pages(self):
		return str(self.__page_results if self.__page_results else random.randint(75, 100))

	def __status(self, count, query, proxy = None, color = "green"):
		text = ("QUERY {0}/{1}: {2}").format(count, len(self.__queries), query)
		if proxy:
			text = ("{0} | PROXY: {1}").format(text, proxy)
		get_timestamp(text, color)

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

	def __check_blacklist(self, urls):
		tmp = []
		for url in urls:
			if not re.search(self.__blacklist, url, self.__flags):
				tmp.append(url)
		return tmp

	def download_files(self, results, directory):
		get_timestamp("Downloading files... Proxies will be ignored...")
		results = self.__get_urls(results)
		progress = Progress(len(results))
		progress.show()
		with concurrent.futures.ThreadPoolExecutor(max_workers = self.__threads) as executor:
			subprocesses = []
			for url in results:
				subprocesses.append(executor.submit(self.__download, url))
			for subprocess in concurrent.futures.as_completed(subprocesses):
				result = subprocess.result()
				if result["data"]:
					write_file_silent(result["data"], get_filename(result["url"], directory))
				progress.show()

	def __get_urls(self, results):
		tmp = []
		for result in results:
			tmp.extend(result["urls"])
		tmp = unique(tmp)
		random.shuffle(tmp)
		return tmp

	def __download(self, url):
		tmp = {"url": url, "data": None}
		session = requests.Session()
		session.max_redirects = 10
		response = None
		try:
			response = session.get(url, headers = self.__get_headers(), proxies = None, timeout = 30, verify = False, allow_redirects = True)
			if response.status_code == 200:
				tmp["data"] = response.content
		except (requests.packages.urllib3.exceptions.LocationParseError, requests.exceptions.RequestException) as ex:
			if self.__debug:
				print(("ERROR: {0}").format(ex))
		finally:
			if response:
				response.close()
			session.close()
		return tmp

# ----------------------------------------

class Proxies:

	def __init__(
		self,
		proxies
	):
		self.__proxies     = proxies
		self.__index       = 0
		self.__round_robin = False

	def available(self):
		return bool(self.__proxies)

	def count(self):
		return len(self.__proxies)

	def round_robin(self):
		tmp = self.__round_robin
		if tmp:
			self.__round_robin = False
		return tmp

	def get_proxy(self):
		proxy = self.__proxies[self.__index]
		self.__index += 1
		if self.__index >= self.count():
			self.__index = 0
			self.__round_robin = True
		return proxy

	def remove_proxy(self, proxy):
		if proxy in self.__proxies:
			self.__proxies.pop(self.__proxies.index(proxy))
			self.__index -= 1
			if self.__index < 0:
				self.__index = 0
			print(("Removing '{0}' due to an error or rate limiting | Proxies left: {1}").format(proxy, self.count()))

# ----------------------------------------

class Progress:

	def __init__(
		self,
		total
	):
		self.__total = total
		self.__count = 0

	def show(self):
		print(("Progress: {0}/{1} | {2:.2f}%").format(self.__count, self.__total, (self.__count / self.__total) * 100), end = "\n" if self.__count == self.__total else "\r")
		self.__count += 1

# ----------------------------------------

# my own validation algorithm

class Validate:

	def __init__(self):
		self.__proceed = True
		self.__args    = {
			"queries"         : None,
			"site"            : None,
			"time"            : None,
			"total-results"   : None,
			"page-results"    : None,
			"minimum-queries" : None,
			"maximum-queries" : None,
			"minimum-pages"   : None,
			"maximum-pages"   : None,
			"agents"          : None,
			"proxies"         : None,
			"directory"       : None,
			"threads"         : None,
			"out"             : None,
			"sleep-on-start"  : None,
			"debug"           : None
		}

	def __basic(self):
		self.__proceed = False
		print("Chad v5.1 ( github.com/ivan-sincek/chad )")
		print("")
		print("Usage:   chad -q queries     [-s site         ] [-a agents         ] [-p proxies    ] [-o out         ]")
		print("Example: chad -q queries.txt [-s *.example.com] [-a user_agents.txt] [-p proxies.txt] [-o results.json]")

	def __advanced(self):
		self.__basic()
		print("")
		print("DESCRIPTION")
		print("    Search Google Dorks like Chad")
		print("QUERIES")
		print("    File with Google Dorks or a single query to use")
		print("    -q <queries> - queries.txt | intext:password | \"ext:tar OR ext:zip\" | etc.")
		print("SITE")
		print("    Domain[s] to search")
		print("    -s <site> - example.com | sub.example.com | *.example.com | \"*.example.com -www\" | etc.")
		print("TIME")
		print("    Get results not older than the specified time in months")
		print("    -t <time> - 6 | 12 | 24 | etc.")
		print("TOTAL RESULTS")
		print("    Total number of unique results")
		print("    Default: 100")
		print("    -tr <total-results> - 200 | etc.")
		print("PAGE RESULTS")
		print("    Number of results per page - capped at 100 by Google")
		print("    Default: randint(75, 100) per page")
		print("    -pr <page-results> - 50 | etc.")
		print("MINIMUM QUERIES")
		print("    Minimum sleep between Google queries")
		print("    Default: 75")
		print("    -min-q <minimum-queries> - 120 | etc.")
		print("MAXIMUM QUERIES")
		print("    Maximum sleep between Google queries")
		print("    Default: minimum-queries + 50")
		print("    -max-q <maximum-queries> - 180 | etc.")
		print("MINIMUM PAGES")
		print("    Minimum sleep between Google pages")
		print("    Default: 15")
		print("    -min-p <minimum-pages> - 30 | etc.")
		print("MAXIMUM PAGES")
		print("    Maximum sleep between Google pages")
		print("    Default: minimum-pages + 10")
		print("    -max-p <maximum-pages> - 60 | etc.")
		print("AGENTS")
		print("    File with user agents to use")
		print("    Default: random")
		print("    -a <agents> - user_agents.txt | etc.")
		print("PROXIES")
		print("    File with proxies or a single proxy to use")
		print("    -p <proxies> - proxies.txt | http://127.0.0.1:8080 | etc.")
		print("DIRECTORY")
		print("    Downloads directory")
		print("    All downloaded files will be saved in this directory")
		print("    -d <directory> - downloads | etc.")
		print("THREADS")
		print("    Number of parallel files to download")
		print("    Default: 5")
		print("    -th <threads> - 20 | etc.")
		print("OUT")
		print("    Output file")
		print("    -o <out> - results.json | etc.")
		print("SLEEP ON START")
		print("    Safety feature to prevent accidental rate limit triggering")
		print("    -sos <sleep-on-start> - no ")
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

	def __validate(self, key, value):
		value = value.strip()
		if len(value) > 0:
			# ----------------------------
			if key == "-q" and self.__args["queries"] is None:
				self.__args["queries"] = value
				if os.path.isfile(self.__args["queries"]):
					if not os.access(self.__args["queries"], os.R_OK):
						self.__error("File with Google Dorks does not have read permission")
					elif not os.stat(self.__args["queries"]).st_size > 0:
						self.__error("File with Google Dorks is empty")
					else:
						self.__args["queries"] = read_file(self.__args["queries"])
						if not self.__args["queries"]:
							self.__error("No Google Dorks were found")
				else:
					self.__args["queries"] = [self.__args["queries"]]
			# ----------------------------
			elif key == "-s" and self.__args["site"] is None:
				self.__args["site"] = value
			# ----------------------------
			elif key == "-t" and self.__args["time"] is None:
				self.__args["time"] = value
				if not self.__args["time"].isdigit():
					self.__error("Number of months must be numeric")
				else:
					self.__args["time"] = int(self.__args["time"])
					if self.__args["time"] < 1:
						self.__error("Number of months must be greater than zero")
			# ----------------------------
			elif key == "-tr" and self.__args["total-results"] is None:
				self.__args["total-results"] = value
				if not self.__args["total-results"].isdigit():
					self.__error("Total number of unique results must be numeric")
				else:
					self.__args["total-results"] = int(self.__args["total-results"])
					if self.__args["total-results"] < 1:
						self.__error("Total number of unique results must be greater than zero")
			# ----------------------------
			elif key == "-pr" and self.__args["page-results"] is None:
				self.__args["page-results"] = value
				if not self.__args["page-results"].isdigit():
					self.__error("Number of results per page must be numeric")
				else:
					self.__args["page-results"] = int(self.__args["page-results"])
					if self.__args["page-results"] < 1 or self.__args["page-results"] > 1000:
						self.__error("Number of results per page must be between 1 and 1000")
			# ----------------------------
			elif key == "-min-q" and self.__args["minimum-queries"] is None:
				self.__args["minimum-queries"] = value
				if not self.__args["minimum-queries"].isdigit():
					self.__error("Minimum sleep between Google queries must be numeric")
				else:
					self.__args["minimum-queries"] = int(self.__args["minimum-queries"])
					if self.__args["minimum-queries"] < 1:
						self.__error("Minimum sleep between Google queries must be greater than zero")
			# ----------------------------
			elif key == "-max-q" and self.__args["maximum-queries"] is None:
				self.__args["maximum-queries"] = value
				if not self.__args["maximum-queries"].isdigit():
					self.__error("Maximum sleep between Google queries must be numeric")
				else:
					self.__args["maximum-queries"] = int(self.__args["maximum-queries"])
					if self.__args["maximum-queries"] < 1:
						self.__error("Maximum sleep between Google queries must be greater than zero")
			# ----------------------------
			elif key == "-min-p" and self.__args["minimum-pages"] is None:
				self.__args["minimum-pages"] = value
				if not self.__args["minimum-pages"].isdigit():
					self.__error("Minimum sleep between Google pages must be numeric")
				else:
					self.__args["minimum-pages"] = int(self.__args["minimum-pages"])
					if self.__args["minimum-pages"] < 1:
						self.__error("Minimum sleep between Google pages must be greater than zero")
			# ----------------------------
			elif key == "-max-p" and self.__args["maximum-pages"] is None:
				self.__args["maximum-pages"] = value
				if not self.__args["maximum-pages"].isdigit():
					self.__error("Maximum sleep between Google pages must be numeric")
				else:
					self.__args["maximum-pages"] = int(self.__args["maximum-pages"])
					if self.__args["maximum-pages"] < 1:
						self.__error("Maximum sleep between Google pages must be greater than zero")
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
			elif key == "-p" and self.__args["proxies"] is None:
				self.__args["proxies"] = value
				if os.path.isfile(self.__args["proxies"]):
					if not os.access(self.__args["proxies"], os.R_OK):
						self.__error("File with proxies does not have read permission")
					elif not os.stat(self.__args["proxies"]).st_size > 0:
						self.__error("File with proxies is empty")
					else:
						self.__args["proxies"] = read_file(self.__args["proxies"])
						if not self.__args["proxies"]:
							self.__error("No proxies were found")
				else:
					self.__args["proxies"] = [self.__args["proxies"]]
			# ----------------------------
			elif key == "-d" and self.__args["directory"] is None:
				self.__args["directory"] = value
				if not os.path.exists(self.__args["directory"]):
					self.__error("Downloads directory does not exists")
			# ----------------------------
			elif key == "-th" and self.__args["threads"] is None:
				self.__args["threads"] = value
				if not self.__args["threads"].isdigit():
					self.__error("Number of parallel files to download must be numeric")
				else:
					self.__args["threads"] = int(self.__args["threads"])
					if self.__args["threads"] < 1:
						self.__error("Number of parallel files to download must be greater than zero")
			# ----------------------------
			elif key == "-o" and self.__args["out"] is None:
				self.__args["out"] = value
			# ----------------------------
			elif key == "-sos" and self.__args["sleep-on-start"] is None:
				self.__args["sleep-on-start"] = value.lower()
				if self.__args["sleep-on-start"] != "no":
					self.__error("Specify 'no' to disable sleep on start")
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
		# --------------------
		argc = len(sys.argv) - 1
		# --------------------
		if argc == 0:
			self.__advanced()
		# --------------------
		elif argc == 1:
			if sys.argv[1] == "-h":
				self.__basic()
			elif sys.argv[1] == "--help":
				self.__advanced()
			else:
				self.__error("Incorrect usage", True)
		# --------------------
		elif argc % 2 == 0 and argc <= len(self.__args) * 2:
			for i in range(1, argc, 2):
				self.__validate(sys.argv[i], sys.argv[i + 1])
			if None in [self.__args["queries"]] or not self.__check(argc):
				self.__error("Missing a mandatory option (-q) and/or optional (-s, -t, -tr, -pr, -min-q, -max-q, -min-p, -max-p, -a, -p, -d, -th, -o, -sos, -dbg)", True)
		# --------------------
		else:
			self.__error("Incorrect usage", True)
		# --------------------
		if self.__proceed:
			if not self.__args["total-results"]:
				self.__args["total-results"] = 100
			if not self.__args["minimum-queries"]:
				self.__args["minimum-queries"] = 75
			if not self.__args["maximum-queries"] or self.__args["minimum-queries"] > self.__args["maximum-queries"]:
				self.__args["maximum-queries"] = self.__args["minimum-queries"] + 50
			if not self.__args["minimum-pages"]:
				self.__args["minimum-pages"] = 15
			if not self.__args["maximum-pages"] or self.__args["minimum-pages"] > self.__args["maximum-pages"]:
				self.__args["maximum-pages"] = self.__args["minimum-pages"] + 10
			if not self.__args["threads"]:
				self.__args["threads"] = 5
		# --------------------
		return self.__proceed
		# --------------------

	def get_arg(self, key):
		return self.__args[key]

# ----------------------------------------

def main():
	validate = Validate()
	if validate.run():
		print("###########################################################################")
		print("#                                                                         #")
		print("#                                Chad v5.1                                #")
		print("#                                  by Ivan Sincek                         #")
		print("#                                                                         #")
		print("# Search Google Dorks like Chad.                                          #")
		print("# GitHub repository at github.com/ivan-sincek/chad.                       #")
		print("# Feel free to donate ETH at 0xbc00e800f29524AD8b0968CEBEAD4cD5C5c1f105.  #")
		print("#                                                                         #")
		print("###########################################################################")
		directory = validate.get_arg("directory")
		out = validate.get_arg("out")
		chad = Chad(
			validate.get_arg("queries"),
			validate.get_arg("site"),
			validate.get_arg("time"),
			validate.get_arg("total-results"),
			validate.get_arg("page-results"),
			validate.get_arg("minimum-queries"),
			validate.get_arg("maximum-queries"),
			validate.get_arg("minimum-pages"),
			validate.get_arg("maximum-pages"),
			validate.get_arg("agents"),
			validate.get_arg("proxies"),
			validate.get_arg("threads"),
			validate.get_arg("sleep-on-start"),
			validate.get_arg("debug")
		)
		chad.validate_queries()
		if not chad.check_queries():
			print("No valid queries are left")
		else:
			results = chad.run()
			if not results:
				print("No results")
			else:
				if directory:
					chad.download_files(results, directory)
				results = jdump(results)
				print(results)
				if out:
					write_file(results, out)
		print(("Script has finished in {0}").format(datetime.datetime.now() - start))

if __name__ == "__main__":
	main()
