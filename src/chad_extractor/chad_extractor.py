#!/usr/bin/env python3

import datetime
import sys
import os
import json
import jq
import threading
import random
import concurrent.futures
import subprocess
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from nagooglesearch import nagooglesearch
import time
import regex as re

start = datetime.datetime.now()

# -------------------------- INFO --------------------------

def basic():
	global proceed
	proceed = False
	print("Chad Extractor v2.6.2 ( github.com/ivan-sincek/chad )")
	print("")
	print("Usage:   chad-extractor -t template      -res results -o out                 [-th threads] [-r retries] [-w wait] [-a agents         ]")
	print("Example: chad-extractor -t template.json -res results -o results_report.json [-th 10     ] [-r 5      ] [-w 10  ] [-a user_agents.txt]")

def advanced():
	basic()
	print("")
	print("DESCRIPTION")
	print("    Extract and validate data from Chad results")
	print("TEMPLATE")
	print("    JSON template file with extract and validate information")
	print("    -t <template> - template.json | etc.")
	print("RESULTS FILE/DIRECTORY")
	print("    Chad results file/directory")
	print("    -res <results> - results | results.json | etc.")
	print("THREADS")
	print("    Number of parallel headless browsers to run")
	print("    Default: 4")
	print("    -th <threads> - 10 | etc.")
	print("RETRIES")
	print("    Number of retries per URL")
	print("    Default: 2")
	print("    -r <retries> - 5 | etc.")
	print("WAIT")
	print("    Wait before fetching the page content")
	print("    Default: 4")
	print("    -w <wait> - 10 | etc.")
	print("AGENTS")
	print("    File with user agents to use")
	print("    Default: nagooglesearch user agents")
	print("    -a <agents> - user_agents.txt | etc.")
	print("OUT")
	print("    Output file")
	print("    -o <out> - results_report.json | etc.")
	print("VERBOSE")
	print("    Create additional supporting output files")
	print("    -v <verbose> - yes")

# ------------------- MISCELENIOUS BEGIN -------------------

def unique(sequence, sort = False):
	seen = set()
	array = [x for x in sequence if not (x in seen or seen.add(x))]
	if sort and array:
		array = sorted(array, key = str.casefold)
	return array

def read_file(file, sort = False):
	tmp = []
	with open(file, "r", encoding = "ISO-8859-1") as stream:
		for line in stream:
			line = line.strip()
			if line:
				tmp.append(line)
	stream.close()
	return unique(tmp, sort)

def read_json(file):
	tmp = []
	try:
		tmp = json.loads(open(file, "r", encoding = "UTF-8").read())
	except Exception:
		pass
	return tmp

def jquery(obj, query):
	tmp = []
	try:
		tmp = jq.compile(query).input(obj).all()
	except Exception:
		pass
	return tmp

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
	open(out, "w").write(data)

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

args = {"template": None, "results": None, "threads": None, "retries": None, "wait": None, "agents": None, "out": None, "verbose": None}

def validate(key, value):
	global args
	value = value.strip()
	if len(value) > 0:
		if key == "-t" and args["template"] is None:
			args["template"] = value
			if not os.path.isfile(args["template"]):
				error("Template file does not exists")
			elif not os.access(args["template"], os.R_OK):
				error("Template file does not have read permission")
			elif not os.stat(args["template"]).st_size > 0:
				error("Template file is empty")
			else:
				args["template"] = read_json(args["template"])
				if not args["template"]:
					error("Template file has invalid JSON format")
		elif key == "-res" and args["results"] is None:
			args["results"] = value
			if not os.path.exists(args["results"]):
				error("Chad results file/directory does not exists")
			elif os.path.isdir(args["results"]):
				args["results"] = os.path.abspath(args["results"])
				args["results"] = [args["results"] + os.path.sep + file for file in os.listdir(args["results"]) if file.endswith(".json")]
				if not args["results"]:
					error("No JSON files were found in Chad results directory")
			else:
				if not os.access(args["results"], os.R_OK):
					error("Chad results file does not have read permission")
				elif not os.stat(args["results"]).st_size > 0:
					error("Chad results file is empty")
				else:
					args["results"] = [args["results"]]
		elif key == "-th" and args["threads"] is None:
			args["threads"] = value
			if not args["threads"].isdigit():
				error("Number of parallel headless browsers must be numeric")
			else:
				args["threads"] = int(args["threads"])
				if args["threads"] < 1:
					error("Number of parallel headless browsers must be greater than zero")
		elif key == "-r" and args["retries"] is None:
			args["retries"] = value
			if not args["retries"].isdigit():
				error("Number of retries per URL must be numeric")
			else:
				args["retries"] = int(args["retries"])
				if args["retries"] < 0:
					error("Number of retries per URL must be greater than or equal to zero")
		elif key == "-w" and args["wait"] is None:
			args["wait"] = value
			if not args["wait"].isdigit():
				error("Wait before fetching the page content must be numeric")
			else:
				args["wait"] = int(args["wait"])
				if args["wait"] < 0:
					error("Wait before fetching the page content must be greater than or equal to zero")
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
		elif key == "-o" and args["out"] is None:
			args["out"] = value
		elif key == "-v" and args["verbose"] is None:
			args["verbose"] = value.lower()
			if args["verbose"] != "yes":
				error("Specify 'yes' to enable verbosity")

def check(argc, args):
	count = 0
	for key in args:
		if args[key] is not None:
			count += 1
	return argc - count == argc / 2

# --------------------- VALIDATION END ---------------------

# ----------------- GLOBAL VARIABLES BEGIN -----------------

data = {
	"extracted": {"data": [], "lock": threading.Lock()},
	"failed_extraction": {"data": [], "lock": threading.Lock()},
	"validated": {"data": [], "lock": threading.Lock()},
	"failed_validation": {"data": [], "lock": threading.Lock()}
}

def extend_data(array, string):
	global data
	for key in data:
		if string == key:
			with data[key]["lock"]:
				data[key]["data"].extend(array)
			break

queries = {
	"get_urls": ".[].urls[]",
	"group_by_url": "group_by(.url) | map((.[0] | del(.file)) + {files: (map(.file) | unique)})[]",
	"sort_by_url": "sort_by(.url | ascii_downcase)[]",
	"delete_files": ".[] | del(.files)",
	"get_results": ".[].results[][]",
	"get_url": ".[].url",
	"get_files": ".[].files[]"
}

# ------------------ GLOBAL VARIABLES END ------------------

# ----------------------- TASK BEGIN -----------------------

def get_timestamp(text):
	return print(("{0} - {1}").format(datetime.datetime.now().strftime("%H:%M:%S"), text))

def split(records, threads = 4):
	if threads > 1:
		k, m = divmod(len(records), threads)
		return (records[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(threads))
	else:
		return [records]

def parse_response(skey, template, record, results, response):
	tmp = None
	if skey == "extracted":
		for key in template:
			matches = re.findall(template[key]["extract"], response, re.IGNORECASE)
			if matches:
				try:
					results["results"][key] = unique([(template[key]["extract_prepend"] if "extract_prepend" in template[key] else "") + match + (template[key]["extract_append"] if "extract_append" in template[key] else "") for match in matches], True)
				except Exception as ex:
					print_error(("{0} | {1}").format(key, ex))
		if results["results"]:
			tmp = results
	elif skey == "validated" and re.search(template[record["id"]]["validate"], response, re.IGNORECASE):
		tmp = results
	return tmp

async def block(route):
	await route.abort() if route.request.resource_type in ["stylesheet", "image", "media", "font", "ping"] else await route.continue_()

async def page_get(context, url, wait = 4):
	tmp = {"response": None, "error": False}
	page = None
	try:
		page = await context.new_page()
		await page.route("**/*", block) # ignore unnecessary requests
		await page.goto(url, wait_until = "load")
		if wait:
			time.sleep(wait)
		try:
			await page.wait_for_load_state(state = "networkidle") # wait until network idle for 500ms within 30s
		except PlaywrightTimeoutError: # in case of a live stream, suppress and continue
			pass
		tmp["response"] = await page.content()
	except PlaywrightTimeoutError:
		pass
	except Exception: # in case of a file or invalid domain, fallback
		tmp["error"] = True
	finally:
		if page is not None:
			await page.close()
	return tmp

async def request_get(context, url):
	tmp = {"response": None, "error": False}
	try:
		response = await context.request.get(url)
		response = await response.body()
		tmp["response"] = response.decode("ISO-8859-1")
	except PlaywrightTimeoutError:
		pass
	except Exception: # in case of an invalid domain, break
		tmp["error"] = True
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

async def browser_requests(skey, fkey, template, records, retries = 2, wait = 4, agents = None):
	succeeded = []
	failed = []
	async with async_playwright() as pw:
		browser = await pw.chromium.launch(headless = True)
		context = await browser.new_context(ignore_https_errors = True, java_script_enabled = True, accept_downloads = False)
		# context.set_default_timeout(60000)
		for record in records:
			results = {"files": record["files"], "url": record["url"], "results": {}}
			count = retries + 1
			while count > 0:
				await context.set_extra_http_headers(get_headers(agents)) # anti-bot evasion 2
				# --------------------
				tmp = await page_get(context, record["url"], wait)
				if tmp["error"]:
					tmp = await request_get(context, record["url"])
					if tmp["error"]:
						count = 0
				# --------------------
				if not tmp["error"] and tmp["response"]:
					count = 0
					results = parse_response(skey, template, record, results, tmp["response"])
					if results:
						succeeded.append(results)
				else:
					count -= 1
					if count <= 0:
						failed.append(results)
				# --------------------
				await context.clear_cookies() # anti-bot evasion 3
		await context.close()
		await browser.close()
	extend_data(succeeded, skey)
	extend_data(failed, fkey)

def proxy_browser_requests(template, records, retries = 2, wait = 4, agents = None, extract = True):
	asyncio.run(browser_requests("extracted" if extract else "validated", "failed_extraction" if extract else "failed_validation", template, records, retries, wait, agents))

def parse_template(template, extract = True):
	tmp = {}
	if extract:
		for key in template:
			if "extract" in template[key]:
				tmp[key] = template[key]
	else:
		for key in template:
			if "validate" in template[key]:
				tmp[key] = template[key]
	return tmp

def parse_input(template, results, extract = True):
	tmp = []
	if extract:
		for file in results:
			for url in jquery(read_json(file), queries["get_urls"]):
				tmp.append({"file": file, "url": url})
	else:
		for result in results:
			for key in result["results"]:
				if key in template:
					for url in result["results"][key]:
						for file in result["files"]:
							tmp.append({"file": file, "url": url, "id": key})
	return tmp

def run(template, results, threads = 4, retries = 2, wait = 4, agents = None, extract = True):
	results = jquery(results, queries["group_by_url"])
	get_timestamp(("Number of URLs to be {0}: {1}").format("extracted" if extract else "validated", len(results)))
	random.shuffle(results) # anti-bot evasion 1
	with concurrent.futures.ThreadPoolExecutor(max_workers = threads) as executor:
		subprocesses = []
		for records in split(results, threads):
			if wait:
				time.sleep(wait)
			subprocesses.append(executor.submit(proxy_browser_requests, template, records, retries, wait, agents, extract))
		concurrent.futures.wait(subprocesses)

def get_record():
	return {"summary": {"validated": [], "extracted": []}, "failed": {"validation": [], "extraction": []}, "full": []}

def parse_results(out, verbose = False):
	global data
	# --------------------
	tmp = get_record()
	# --------------------
	data["extracted"]["data"] = jquery(data["extracted"]["data"], queries["sort_by_url"])
	tmp["full"] = jquery(data["extracted"]["data"], queries["delete_files"])
	tmp["summary"]["extracted"] = unique(jquery(tmp["full"], queries["get_results"]), True)
	# --------------------
	data["failed_extraction"]["data"] = jquery(data["failed_extraction"]["data"], queries["sort_by_url"])
	tmp["failed"]["extraction"] = jquery(data["failed_extraction"]["data"], queries["get_url"])
	# --------------------
	data["validated"]["data"] = jquery(data["validated"]["data"], queries["sort_by_url"])
	tmp["summary"]["validated"] = jquery(data["validated"]["data"], queries["get_url"])
	# --------------------
	data["failed_validation"]["data"] = jquery(data["failed_validation"]["data"], queries["sort_by_url"])
	tmp["failed"]["validation"] = jquery(data["failed_validation"]["data"], queries["get_url"])
	# --------------------
	write_file(jdump(tmp), out)
	# --------------------
	if verbose:
		for file in unique(jquery(data["extracted"]["data"], queries["get_files"])):
			# --------------------
			tmp = get_record()
			# --------------------
			tmp["full"] = jquery(data["extracted"]["data"], (".[] | select(.files | index(\"{0}\")) | del(.files)").format(file))
			tmp["summary"]["extracted"] = unique(jquery(tmp["full"], queries["get_results"]), True)
			# --------------------
			query = (".[] | select(.files | index(\"{0}\")) | .url").format(file)
			# --------------------
			tmp["failed"]["extraction"] = jquery(data["failed_extraction"]["data"], query)
			# --------------------
			tmp["summary"]["validated"] = jquery(data["validated"]["data"], query)
			# --------------------
			tmp["failed"]["validation"] = jquery(data["failed_validation"]["data"], query)
			# --------------------
			write_file_silent(jdump(tmp), file.replace(".json", ".report.json"))
			# --------------------

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
		if args["template"] is None or args["results"] is None or args["out"] is None or not check(argc, args):
			error("Missing a mandatory option (-t, -res, -o) and/or optional (-th, -r, -w, -a, -v)", True)
	else:
		error("Incorrect usage", True)

	if proceed:
		print("######################################################################")
		print("#                                                                    #")
		print("#                        Chad Extractor v2.6.2                       #")
		print("#                                  by Ivan Sincek                    #")
		print("#                                                                    #")
		print("# Extract and validate data from Chad results.                       #")
		print("# GitHub repository at github.com/ivan-sincek/chad.                  #")
		print("# Feel free to donate bitcoin at 1BrZM6T7G9RN8vbabnfXu4M6Lpgztq6Y14. #")
		print("#                                                                    #")
		print("######################################################################")
		# --------------------
		if not args["threads"]:
			args["threads"] = 4
		if not args["retries"]:
			args["retries"] = 2
		if not args["wait"]:
			args["wait"] = 4
		# --------------------
		args["template"] = parse_template(args["template"], True)
		if not args["template"]:
			print("No extraction entries were found in the template file")
		else:
			args["results"] = parse_input(args["template"], args["results"], True)
			if not args["results"]:
				print("No results for data extraction were found")
			else:
				run(args["template"], args["results"], args["threads"], args["retries"], args["wait"], args["agents"], True)
				if not data["extracted"]["data"]:
					print("No data was extracted")
				else:
					args["template"] = parse_template(args["template"], False)
					if not args["template"]:
						print("No validation entries were found in the template file")
					else:
						args["results"] = parse_input(args["template"], data["extracted"]["data"], False)
						if not args["results"]:
							print("No results for data validation were found")
						else:					
							run(args["template"], args["results"], args["threads"], args["retries"], args["wait"], args["agents"], False)
							if not data["validated"]["data"]:
								print("No data matched the validation criteria")
					parse_results(args["out"], args["verbose"])
		print(("Script has finished in {0}").format(datetime.datetime.now() - start))

if __name__ == "__main__":
	main()

# ------------------------ TASK END ------------------------
