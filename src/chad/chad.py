#!/usr/bin/env python3

import alive_progress, argparse, colorama, concurrent.futures, datetime, dateutil.relativedelta as relativedelta, json, os, random, regex as re, requests, sys, termcolor, threading, time, urllib.parse
from   nagooglesearch import nagooglesearch

colorama.init(autoreset = True)

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# ----------------------------------------

class Stopwatch:

	def __init__(self):
		self.__start = datetime.datetime.now()

	def stop(self):
		self.__end = datetime.datetime.now()
		print(f"Script has finished in {self.__end - self.__start}")

stopwatch = Stopwatch()

# ----------------------------------------

def parse_float(value):
	tmp = None
	try:
		tmp = float(value)
	except ValueError:
		pass
	return tmp

def get_filename(url, directory):
	url = urllib.parse.urlsplit(url)
	base = os.path.join(directory, url.netloc)
	if url.path:
		base = os.path.join(directory, url.path.strip("/").rsplit("/", 1)[-1])
	count = 0
	filename = base
	while os.path.exists(filename):
		count += 1
		filename = f"{base} ({count})"
	return filename

def unique(sequence):
	seen = set()
	return [x for x in sequence if not (x in seen or seen.add(x))]

def read_file(file):
	tmp = []
	with open(file, "r", encoding = "ISO-8859-1") as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	return unique(tmp)

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

def write_file_silent(data, out):
	try:
		open(out, "wb").write(data)
	except FileNotFoundError:
		pass

def jdump(data):
	return json.dumps(data, indent = 4, ensure_ascii = False) if data else ""

def get_timestamp(text, color = None):
	text = f"{datetime.datetime.now().strftime('%H:%M:%S')} - {text}"
	termcolor.cprint(text, color) if color else print(text)

# ----------------------------------------

class Chad:

	def __init__(self, queries, site, time, total_results, page_results, minimum_queries, maximum_queries, minimum_pages, maximum_pages, user_agents, proxies, threads, sleep_on_start, debug):
		self.__queries         = queries
		self.__site            = site
		self.__tbs             = self.__init_tbs(time)
		self.__total_results   = total_results
		self.__page_results    = page_results
		self.__minimum_queries = minimum_queries
		self.__maximum_queries = maximum_queries
		self.__minimum_pages   = minimum_pages
		self.__maximum_pages   = maximum_pages
		self.__user_agents     = user_agents
		self.__user_agents_len = len(self.__user_agents)
		self.__proxies         = Proxies(proxies)
		self.__threads         = threads
		self.__sleep_on_start  = sleep_on_start
		self.__debug           = debug
		self.__print_lock      = threading.Lock()
		self.__blacklist       = self.__init_blacklist()
		self.__flags           = re.MULTILINE | re.IGNORECASE

	def __init_tbs(self, time):
		tmp = "li:1"
		if time:
			tmp = datetime.datetime.today()
			tmp = nagooglesearch.get_tbs(tmp, tmp - relativedelta.relativedelta(months = time))
		return tmp

	def __init_blacklist(self):
		# exclude security-related websites that contain Google Dorks to minimize false positives
		blacklist = ["kb.cert.org", "exploit-db.com"]
		for entry in ["dork", "hack"]:
			for delimiter in ["", "+", "-", "_", "%20"]:
				blacklist.append("google" + delimiter + entry)
		blacklist = ("(?:{0})").format(("|").join([entry.replace(".", "\\.").replace("/", "\\/") for entry in blacklist]))
		return blacklist

	def has_queries(self):
		return bool(self.__queries)

	def validate_queries(self):
		get_timestamp("Validating Google Dorks...")
		print("Google only allows queries up to 32 words in length, separated by spaces")
		tmp = []
		ignored = []
		for query in self.__queries:
			if self.__site:
				if self.__get_site(query):
					ignored.append(query)
					continue
				query = f"site:{self.__site} {query}"
			if len(query.split(" ")) > 32:
				ignored.append(query)
				continue
			tmp.append(query)
		if ignored:
			self.__print_ignored(ignored)
		self.__queries = unique(tmp)

	def __get_site(self, query):
		return re.search(r"(?<!in|\-)site\:", query, flags = self.__flags)

	def __print_ignored(self, ignored, color = "cyan"):
		print(f"IGNORED QUERIES: {len(ignored)}")
		for query in ignored:
			termcolor.cprint(query, color) if color else print(query)

	def run(self):
		get_timestamp("Searching Google Dorks...")
		print("Press CTRL + C to exit early - results will be saved")
		results = []
		count = 0
		exit_program = False
		try:
			if self.__sleep_on_start:
				self.__wait()
			for query in self.__queries:
				count += 1
				entry = {"query": query, "proxy": None, "urls": None}
				search_parameters = {
					"q"     : entry["query"],
					"tbs"   : self.__tbs,
					"hl"    : "en",
					"filter": "0",
					"safe"  : "images",
					"num"   : self.__get_num_pages()
				}
				while not exit_program:
					# --------------------
					if self.__proxies.has_proxies():
						if self.__proxies.round_robin():
							self.__wait()
						entry["proxy"] = self.__proxies.get_proxy()
					elif count > 1:
						self.__wait()
					# --------------------
					self.__status(count, entry["query"], entry["proxy"])
					client = nagooglesearch.SearchClient(
						tld               = "com",
						search_parameters = search_parameters,
						user_agent        = self.__get_user_agent(),
						proxy             = entry["proxy"],
						max_results       = self.__total_results,
						min_sleep         = self.__minimum_pages,
						max_sleep         = self.__maximum_pages,
						debug             = self.__debug
					)
					entry["urls"] = client.search()
					# --------------------
					remove_proxy = False
					error = client.get_error()
					if error:
						termcolor.cprint(error, "yellow")
						if error == "INIT_ERROR":
							exit_program = True
						elif error == "REQUESTS_EXCEPTION" or error == "429_TOO_MANY_REQUESTS":
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
						if not self.__proxies.has_proxies():
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
		print(f"Sleeping between Google queries for {seconds} sec...")
		time.sleep(seconds)

	def __get_num_pages(self):
		return str(self.__page_results if self.__page_results else random.randint(75, 100))

	def __status(self, count, query, proxy = None, color = "green"):
		text = f"QUERY {count}/{len(self.__queries)}: {query}"
		if proxy:
			text = f"{text} | PROXY: {proxy}"
		get_timestamp(text, color)

	def __get_headers(self):
		return {
			"User-Agent": self.__get_user_agent(),
			"Accept-Language": "*",
			"Accept": "*/*",
			"Connection": "keep-alive",
			"Referer": "https://www.google.com/",
			"Upgrade-Insecure-Requests": "1"
		}

	def __get_user_agent(self):
		return self.__user_agents[random.randint(0, self.__user_agents_len - 1)]

	def __check_blacklist(self, urls):
		tmp = []
		for url in urls:
			if not re.search(self.__blacklist, url, flags = self.__flags):
				tmp.append(url)
		return tmp

	def download_files(self, results, directory):
		get_timestamp("Downloading files... Ignoring proxies...")
		results = self.__get_urls(results)
		with alive_progress.alive_bar(len(results), title = "Progress:") as bar:
			with concurrent.futures.ThreadPoolExecutor(max_workers = self.__threads) as executor:
				subprocesses = []
				for url in results:
					subprocesses.append(executor.submit(self.__download, url))
				for subprocess in concurrent.futures.as_completed(subprocesses):
					result = subprocess.result()
					if result["data"]:
						write_file_silent(result["data"], get_filename(result["url"], directory))
					bar()

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
				with self.__print_lock:
					print(f"ERROR: {ex}")
		finally:
			if response:
				response.close()
			session.close()
		return tmp

# ----------------------------------------

class Proxies:

	def __init__(self, proxies):
		self.__proxies     = proxies
		self.__index       = 0
		self.__round_robin = False

	def has_proxies(self):
		return bool(self.__proxies)

	def round_robin(self):
		tmp = self.__round_robin
		if tmp:
			self.__round_robin = False
		return tmp

	def get_proxy(self):
		proxy = self.__proxies[self.__index]
		self.__index += 1
		if self.__index >= len(self.__proxies):
			self.__index = 0
			self.__round_robin = True
		return proxy

	def remove_proxy(self, proxy):
		if proxy in self.__proxies:
			self.__proxies.pop(self.__proxies.index(proxy))
			self.__index -= 1
			if self.__index < 0:
				self.__index = 0
			print(f"Removing '{proxy}' due to an error or rate limiting | Proxies left: {len(self.__proxies)}")

# ----------------------------------------

class MyArgParser(argparse.ArgumentParser):

	def print_help(self):
		print("Chad v6.6 ( github.com/ivan-sincek/chad )")
		print("")
		print("Usage:   chad -q queries     [-s site         ] [-x proxies    ] [-o out         ]")
		print("Example: chad -q queries.txt [-s *.example.com] [-x proxies.txt] [-o results.json]")
		print("")
		print("DESCRIPTION")
		print("    Search Google Dorks like Chad")
		print("QUERIES")
		print("    File with Google Dorks or a single query to use")
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
		print("    Default: randint(75, 100)")
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
		print("    -a, --user-agents = curl/3.30.1 | user_agents.txt | random[-all] | etc.")
		print("PROXIES")
		print("    File with proxies or a single proxy to use")
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
		print("    Safety feature to prevent triggering rate limits accidentally, enabled by default")
		print("    -nsos, --no-sleep-on-start")
		print("DEBUG")
		print("    Debug output")
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
		self.__proceed = True
		self.__parser  = MyArgParser()
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

	def run(self):
		self.__args                 = self.__parser.parse_args()
		self.__args.queries         = self.__parse_queries(self.__args.queries)                               # required
		self.__args.time            = self.__parse_time(self.__args.time)                                     if self.__args.time            else 0
		self.__args.total_results   = self.__parse_total_results(self.__args.total_results)                   if self.__args.total_results   else 100
		self.__args.page_results    = self.__parse_page_results(self.__args.page_results)                     if self.__args.page_results    else 0
		self.__args.minimum_queries = self.__parse_min_max(self.__args.minimum_queries, "minimum", "queries") if self.__args.minimum_queries else 75
		self.__args.maximum_queries = self.__parse_min_max(self.__args.maximum_queries, "maximum", "queries") if self.__args.maximum_queries else (self.__args.minimum_queries + 50 if self.__proceed else 125)
		self.__args.minimum_pages   = self.__parse_min_max(self.__args.minimum_pages, "minimum", "pages")     if self.__args.minimum_pages   else 15
		self.__args.maximum_pages   = self.__parse_min_max(self.__args.maximum_pages, "maximum", "pages")     if self.__args.maximum_pages   else (self.__args.minimum_pages + 10 if self.__proceed else 25)
		self.__args.user_agents     = self.__parse_user_agents(self.__args.user_agents)                       if self.__args.user_agents     else nagooglesearch.get_all_user_agents()
		self.__args.proxies         = self.__parse_proxies(self.__args.proxies)                               if self.__args.proxies         else []
		self.__args.directory       = self.__parse_directory(self.__args.directory)                           if self.__args.directory       else ""
		self.__args.threads         = self.__parse_threads(self.__args.threads)                               if self.__args.threads         else 5
		self.__args                 = vars(self.__args)
		return self.__proceed

	def get_arg(self, key):
		return self.__args[key]

	def __error(self, msg):
		self.__proceed = False
		self.__print_error(msg)

	def __print_error(self, msg):
		print(f"ERROR: {msg}")

	def __parse_queries(self, value):
		tmp = []
		if os.path.isfile(value):
			if not os.access(value, os.R_OK):
				self.__error("File with Google Dorks does not have a read permission")
			elif not os.stat(value).st_size > 0:
				self.__error("File with Google Dorks is empty")
			else:
				tmp = read_file(value)
				if not tmp:
					self.__error("No Google Dorks were found")
		else:
			tmp.append(value)
		return tmp

	def __parse_time(self, value):
		if not value.isdigit():
			self.__error("Number of months must be numeric")
		else:
			value = int(value)
			if value <= 0:
				self.__error("Number of months must be greater than zero")
		return value

	def __parse_total_results(self, value):
		if not value.isdigit():
			self.__error("Total number of unique results must be numeric")
		else:
			value = int(value)
			if value <= 0:
				self.__error("Total number of unique results must be greater than zero")
		return value

	def __parse_page_results(self, value):
		if not value.isdigit():
			self.__error("Number of results per page must be numeric")
		else:
			value = int(value)
			if value <= 0 or value > 100:
				self.__error("Number of results per page must be between 1 and 100")
		return value

	def __parse_min_max(self, value, scope, target):
		scope = scope.capitalize()
		target = target.lower()
		value = parse_float(value)
		if value is None:
			self.__error(f"{scope} sleep time between Google {target} must be numeric")
		elif value <= 0:
			self.__error(f"{scope} sleep time between Google {target} must be greater than zero")
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

	def __parse_proxies(self, value):
		tmp = []
		if os.path.isfile(value):
			if not os.access(value, os.R_OK):
				self.__error("File with proxies does not have a read permission")
			elif not os.stat(value).st_size > 0:
				self.__error("File with proxies is empty")
			else:
				tmp = read_file(value)
				if not tmp:
					self.__error("No proxies were found")
		else:
			tmp = [value]
		return tmp

	def __parse_directory(self, value):
		if not os.path.isdir(value):
			self.__error("Downloads directory does not exist or is not a directory")
		return value

	def __parse_threads(self, value):
		if not value.isdigit():
			self.__error("Number of files to download in parallel must be numeric")
		else:
			value = int(value)
			if value <= 0:
				self.__error("Number of files to download in parallel must be greater than zero")
		return value

# ----------------------------------------

def main():
	validate = Validate()
	if validate.run():
		print("###########################################################################")
		print("#                                                                         #")
		print("#                                Chad v6.6                                #")
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
			validate.get_arg("total_results"),
			validate.get_arg("page_results"),
			validate.get_arg("minimum_queries"),
			validate.get_arg("maximum_queries"),
			validate.get_arg("minimum_pages"),
			validate.get_arg("maximum_pages"),
			validate.get_arg("user_agents"),
			validate.get_arg("proxies"),
			validate.get_arg("threads"),
			not validate.get_arg("no_sleep_on_start"),
			validate.get_arg("debug")
		)
		chad.validate_queries()
		if not chad.has_queries():
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
		stopwatch.stop()

if __name__ == "__main__":
	main()
