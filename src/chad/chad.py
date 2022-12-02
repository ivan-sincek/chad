#!/usr/bin/env python3

import datetime
import dateutil.relativedelta as relativedelta
import sys
import os
import termcolor
import time
import random
from nagooglesearch import nagooglesearch
import regex as re
import concurrent.futures
import subprocess
import requests
import urllib.parse
import json

start = datetime.datetime.now()

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# -------------------------- INFO --------------------------

def basic():
	global proceed
	proceed = False
	print("Chad v2.6.2 ( github.com/ivan-sincek/chad )")
	print("")
	print("Usage:   chad -q queries     [-s site         ] [-a agents         ] [-p proxies    ] [-o out         ]")
	print("Example: chad -q queries.txt [-s *.example.com] [-a user_agents.txt] [-p proxies.txt] [-o results.json]")

def advanced():
	basic()
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
	print("MINIMUM")
	print("    Minimum sleep between queries")
	print("    Default: 75")
	print("    -min <minimum> - 120 | etc.")
	print("MAXIMUM")
	print("    Maximum sleep between queries")
	print("    Default: minimum + 50")
	print("    -max <maximum> - 180 | etc.")
	print("AGENTS")
	print("    File with user agents to use")
	print("    Default: nagooglesearch user agents")
	print("    -a <agents> - user_agents.txt | etc.")
	print("PROXIES")
	print("    File with proxies to use")
	print("    -p <proxies> - proxies.txt | etc.")
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

# ------------------- MISCELENIOUS BEGIN -------------------

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
	stream.close()
	return unique(tmp)

def jdump(data):
	return json.dumps(data, indent = 4, ensure_ascii = False)

def write_file(data, out):
	confirm = "yes"
	if os.path.isfile(out):
		print(("'{0}' already exists").format(out))
		confirm = input("Overwrite the output file (yes): ")
	if confirm.lower() == "yes":
		open(out, "w").write(data)
		print(("Results have been saved to '{0}'").format(out))

def write_file_silent(data, out):
	open(out, "wb").write(data)

# -------------------- MISCELENIOUS END --------------------

# -------------------- VALIDATION BEGIN --------------------

# my own validation algorithm

proceed = True

def print_error(msg):
	print(("ERROR: {0}").format(msg))

def error(msg, help = False):
	global proceed
	proceed = False
	print_error(msg)
	if help:
		print("Use -h for basic and --help for advanced info")

args = {"queries": None, "site": None, "time": None, "total": None, "page": None, "minimum": None, "maximum": None, "sleep": None, "proxies": None, "agents": None, "out": None, "threads": None, "directory": None, "debug": None}

# TO DO: Better site validation.
def validate(key, value):
	global args
	value = value.strip()
	if len(value) > 0:
		if key == "-q" and args["queries"] is None:
			args["queries"] = value
			if os.path.isdir(args["queries"]):
				error("File with Google Dorks is directory")
			elif os.path.isfile(args["queries"]):
				if not os.access(args["queries"], os.R_OK):
					error("File with Google Dorks does not have read permission")
				elif not os.stat(args["queries"]).st_size > 0:
					error("File with Google Dorks is empty")
				else:
					args["queries"] = read_file(args["queries"])
					if not args["queries"]:
						error("No Google Dorks were found")
			else:
				args["queries"] = [args["queries"]]
		elif key == "-s" and args["site"] is None:
			args["site"] = value
		elif key == "-t" and args["time"] is None:
			args["time"] = value
			if not args["time"].isdigit():
				error("Number of months must be numeric")
			else:
				args["time"] = int(args["time"])
				if args["time"] < 1:
					error("Number of months must be greater than zero")
		elif key == "-tr" and args["total"] is None:
			args["total"] = value
			if not args["total"].isdigit():
				error("Total number of unique results must be numeric")
			else:
				args["total"] = int(args["total"])
				if args["total"] < 1:
					error("Total number of unique results must be greater than zero")
		elif key == "-pr" and args["page"] is None:
			args["page"] = value
			if not args["page"].isdigit():
				error("Number of results per page must be numeric")
			else:
				args["page"] = int(args["page"])
				if args["page"] < 1 or args["page"] > 1000:
					error("Number of results per page must be between 1 and 1000")
		elif key == "-min" and args["minimum"] is None:
			args["minimum"] = value
			if not args["minimum"].isdigit():
				error("Minimum sleep between queries must be numeric")
			else:
				args["minimum"] = int(args["minimum"])
				if args["minimum"] < 1:
					error("Minimum sleep between queries must be greater than zero")
		elif key == "-max" and args["maximum"] is None:
			args["maximum"] = value
			if not args["maximum"].isdigit():
				error("Maximum sleep between queries must be numeric")
			else:
				args["maximum"] = int(args["maximum"])
				if args["maximum"] < 1:
					error("Maximum sleep between queries must be greater than zero")
		elif key == "-a" and args["agents"] is None:
			args["agents"] = value
			if not os.path.isfile(args["agents"]):
				error("File with user agents does not exists")
			elif not os.access(args["agents"], os.R_OK):
				error("File with user agents does not have read permission")
			elif not os.stat(args["agents"]).st_size > 0:
				error("File with user agents is empty")
			else:
				args["agents"] = read_file(args["agents"])
				if not args["agents"]:
					error("No user agents were found")
		elif key == "-p" and args["proxies"] is None:
			args["proxies"] = value
			if not os.path.isfile(args["proxies"]):
				error("File with proxies does not exists")
			elif not os.access(args["proxies"], os.R_OK):
				error("File with proxies does not have read permission")
			elif not os.stat(args["proxies"]).st_size > 0:
				error("File with proxies is empty")
			else:
				args["proxies"] = read_file(args["proxies"])
				if not args["proxies"]:
					error("No proxies were found")
		elif key == "-d" and args["directory"] is None:
			args["directory"] = os.path.abspath(value)
			if not os.path.exists(args["directory"]):
				error("Downloads directory does not exists")
		elif key == "-th" and args["threads"] is None:
			args["threads"] = value
			if not args["threads"].isdigit():
				error("Number of parallel files to download must be numeric")
			else:
				args["threads"] = int(args["threads"])
				if args["threads"] < 1:
					error("Number of parallel files to download must be greater than zero")
		elif key == "-o" and args["out"] is None:
			args["out"] = value
		elif key == "-sos" and args["sleep"] is None:
			args["sleep"] = value.lower()
			if args["sleep"] != "no":
				error("Specify 'no' to disable sleep on start")
		elif key == "-dbg" and args["debug"] is None:
			args["debug"] = value.lower()
			if args["debug"] != "yes":
				error("Specify 'yes' to enable debug output")

def check(argc, args):
	count = 0
	for key in args:
		if args[key] is not None:
			count += 1
	return argc - count == argc / 2

# --------------------- VALIDATION END ---------------------

# ----------------------- TASK BEGIN -----------------------

def get_timestamp(text):
	return print(("{0} - {1}").format(datetime.datetime.now().strftime("%H:%M:%S"), text))

def status(current, total, query, proxy = None, color = "green"):
	text = ("QUERY {0}/{1}: {2}").format(current, total, termcolor.colored(query, color))
	if proxy:
		text = ("{0} | PROXY: {1}").format(text, proxy)
	get_timestamp(text)

def print_ignored(ignored, color = "cyan"):
	print(("{0} QUERIES IGNORED:").format(len(ignored)))
	for query in ignored:
		print(termcolor.colored(query, color))

def get_site(query):
	return re.search(r"(?<!in|\-)site\:", query, re.IGNORECASE)

def validate_queries(queries, site = None):
	tmp = []
	ignored = []
	const = " "
	for query in queries:
		if site:
			if get_site(query):
				ignored.append(query)
				continue
			query = ("site:{0}{1}({2})").format(site, const, query)
		if len(query.split(const)) > 32:
			ignored.append(query)
			continue
		tmp.append(query)
	if ignored:
		print_ignored(ignored)
	return unique(tmp)

def wait(minimum, maximum):
	sec = random.randint(minimum, maximum)
	print(("Sleeping between requests for {0} seconds...").format(sec))
	time.sleep(sec)

index = 0
round_robin = False

def get_proxy(proxies):
	global index, round_robin
	proxy = proxies[index]
	index += 1
	if index >= len(proxies):
		index = 0
		round_robin = True
	return proxy

def remove_proxy(proxies, proxy, color = "red"):
	global index
	proxies.pop(proxies.index(proxy))
	index -= 1
	if index < 0:
		index = 0
	print(("Proxy '{0}' has been removed due to an error or rate limiting | Proxies left: {1}").format(proxy, len(proxies)))
	return proxies

def check_blacklist(urls):
	# exclude security related websites that contain Google Dorks to minimize false positive results
	blacklist = ["kb.cert.org", "exploit-db.com"]
	for entry in ["dork", "hack"]:
		for delimiter in ["", "+", "-", "_", "%20"]:
			blacklist.append("google" + delimiter + entry)
	blacklist = ("({0})").format(("|").join([entry.replace(".", "\\.").replace("/", "\\/") for entry in blacklist]))
	tmp = []
	for url in urls:
		if not re.search(blacklist, url, re.IGNORECASE):
			tmp.append(url)
	return tmp

def get_tbs(months = None):
	tmp = "li:1"
	if months:
		today = datetime.datetime.today()
		tmp = nagooglesearch.get_tbs(today, today - relativedelta.relativedelta(months = months))
	return tmp

def run(queries, tbs = "li:1", total = 100, page = None, minimum = 75, maximum = 125, agents = None, proxies = None, sleep = False, debug = False):
	global round_robin
	get_timestamp("Searching Google Dorks...")
	print("Press CTRL + C to exit early - all results will be saved")
	results = []
	try:
		if not sleep:
			wait(minimum, maximum)
		count = 0
		length = len(queries)
		exit = False
		for query in queries:
			count += 1
			entry = {"query": query, "proxy": None, "urls": None}
			parameters = {
				"q": entry["query"],
				"tbs": tbs,
				"num": str(page if page else random.randint(75, 100)),
				"hl": "en",
				"filter": "0",
				"safe": "images"
			}
			while not exit:
				if proxies:
					if round_robin:
						wait(minimum, maximum)
						round_robin = False
					entry["proxy"] = get_proxy(proxies)
				elif count > 1:
					wait(minimum, maximum)
				status(count, length, entry["query"], entry["proxy"])
				remove = False
				try:
					client = nagooglesearch.SearchClient(
						tld = "com",
						parameters = parameters,
						max_results = total,
						user_agent = agents[random.randint(0, len(agents) - 1)] if agents else None,
						proxy = entry["proxy"],
						min_sleep = 11,
						max_sleep = 22,
						verbose = debug
					)
					entry["urls"] = client.search()
					if "429_TOO_MANY_REQUESTS" in entry["urls"]:
						print(termcolor.colored("[ HTTP 429 Too Many Requests ]", "yellow"))
						entry["urls"].pop(entry["urls"].index("429_TOO_MANY_REQUESTS"))
						if entry["proxy"]:
							remove = True
						else:
							exit = True
					if entry["urls"]:
						if not get_site(entry["query"]):
							entry["urls"] = check_blacklist(entry["urls"])
						results.append(entry)
					if not remove and not exit:
						break
				except Exception as ex:
					if debug:
						print_error(ex)
					if entry["proxy"]:
						remove = True
					else:
						exit = True
				if remove:
					proxies = remove_proxy(proxies, entry["proxy"])
					if not proxies:
						print_error("All proxies has been exhausted!")
						exit = True
			if exit:
				break
	except KeyboardInterrupt:
		pass
	return results

def get_filename(directory, url):
	url = urllib.parse.urlparse(url)
	base = directory + os.path.sep
	if url.path:
		array = url.path.strip("/").split("/")
		base += array[-1] if len(array) > 1 else array[0]
	else:
		base += url.netloc
	count = 0
	filename = base
	while os.path.exists(filename):
		count += 1
		filename = ("{0} ({1})").format(base, count)
	return filename

def download(url, headers = None, debug = None):
	tmp = {"url": url, "data": None}
	session = requests.Session()
	session.max_redirects = 10
	response = None
	try:
		response = session.get(url, headers = headers, proxies = None, timeout = 90, verify = False, allow_redirects = True)
		if response.status_code == 200:
			tmp["data"] = response.content
	except requests.exceptions.RequestException as ex:
		if debug:
			print_error(ex)
	finally:
		if response is not None:
			response.close()
		session.close()
	return tmp

def get_headers(agents = None):
	return {
		"Accept": "*/*",
		"Accept-Language": "*",
		"Connection": "keep-alive",
		"Referer": "https://www.google.com/",
		# "Upgrade-Insecure-Requests": "1", # because of this request header, some websites might return wrong page content
		"User-Agent": agents[random.randint(0, len(agents) - 1)] if agents else nagooglesearch.get_random_user_agent()
	}

def get_urls(results):
	tmp = []
	for result in results:
		tmp.extend(result["urls"])
	tmp = unique(tmp)
	random.shuffle(tmp)
	return tmp

def progress(count, total):
	print(("Progress: {0}/{1} | {2:.2f}%").format(count, total, (count / total) * 100), end = "\n" if count == total else "\r")

def download_files(results, directory, threads = 5, agents = None, debug = None):
	get_timestamp("Downloading files... Proxies will be ignored...")
	results = get_urls(results)
	count = 0
	total = len(results)
	progress(count, total)
	with concurrent.futures.ThreadPoolExecutor(max_workers = threads) as executor:
		subprocesses = []
		for url in results:
			subprocesses.append(executor.submit(download, url, get_headers(agents), debug))
		for subprocess in concurrent.futures.as_completed(subprocesses):
			result = subprocess.result()
			if result["data"]:
				write_file_silent(result["data"], get_filename(directory, result["url"]))
			count += 1
			progress(count, total)

def main():
	argc = len(sys.argv) - 1

	if argc == 0:
		advanced()
	elif argc == 1:
		if sys.argv[1] == "-h":
			basic()
		elif sys.argv[1] == "--help":
			advanced()
		else:
			error("Incorrect usage", True)
	elif argc % 2 == 0 and argc <= len(args) * 2:
		for i in range(1, argc, 2):
			validate(sys.argv[i], sys.argv[i + 1])
		if args["queries"] is None or not check(argc, args):
			error("Missing a mandatory option (-q) and/or optional (-s, -t, -tr, -pr, -min, -max, -a, -p, -th, -d, -o, -sos, -dbg)", True)
	else:
		error("Incorrect usage", True)

	if proceed:
		print("#######################################################################")
		print("#                                                                     #")
		print("#                             Chad v2.6.2                             #")
		print("#                                  by Ivan Sincek                     #")
		print("#                                                                     #")
		print("# Search Google Dorks like Chad.                                      #")
		print("# GitHub repository at github.com/ivan-sincek/chad.                   #")
		print("# Feel free to donate bitcoin at 1BrZM6T7G9RN8vbabnfXu4M6Lpgztq6Y14.  #")
		print("#                                                                     #")
		print("#######################################################################")
		# --------------------
		if not args["total"]:
			args["total"] = 100
		if not args["minimum"]:
			args["minimum"] = 75
		if not args["maximum"] or args["minimum"] > args["maximum"]:
			args["maximum"] = args["minimum"] + 50
		if not args["threads"]:
			args["threads"] = 5
		# --------------------
		get_timestamp("Validating Google Dorks...")
		print("Google only allows queries up to 32 words in length separated by space")
		args["queries"] = validate_queries(args["queries"], args["site"])
		if not args["queries"]:
			print("No valid queries are left")
		else:
			results = run(args["queries"], get_tbs(args["time"]), args["total"], args["page"], args["minimum"], args["maximum"], args["agents"], args["proxies"], args["sleep"], args["debug"])
			if not results:
				print("No results")
			else:
				if args["directory"]:
					download_files(results, args["directory"], args["threads"], args["agents"], args["debug"])
				results = jdump(results)
				print(results)
				if args["out"]:
					write_file(results, args["out"])
		print(("Script has finished in {0}").format(datetime.datetime.now() - start))

if __name__ == "__main__":
	main()

# ------------------------ TASK END ------------------------
