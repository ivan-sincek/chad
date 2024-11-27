#!/usr/bin/env python3

from . import general, input, result, storage, url

from playwright.async_api     import TimeoutError as PlaywrightTimeoutError
from playwright._impl._errors import Error        as PlaywrightError

import asyncio, multiprocessing, random, scrapy, scrapy.crawler, scrapy.utils.project, typing

# ----------------------------------------

class ChadExtractorSpider(scrapy.Spider):

	def __init__(
		self,
		shared_storage : storage.Shared,
		playwright     : bool,
		playwright_wait: float,
		request_timeout: float,
		user_agents    : list[str],
		proxy          : str,
		debug          : bool
	):
		"""
		Class for managing Scrapy's spider.
		"""
		self.name                   = "ChadExtractorSpider"
		self.handle_httpstatus_list = [401, 403, 404]
		self.__shared_storage       = shared_storage
		self.__validation_started   = self.__shared_storage.is_validation_started()
		self.__playwright           = playwright
		self.__playwright_wait      = playwright_wait
		self.__request_timeout      = request_timeout
		self.__user_agents          = user_agents
		self.__user_agents_len      = len(self.__user_agents)
		self.__proxy                = proxy
		self.__debug                = debug
		self.__context              = 0

	def start_requests(self):
		"""
		Main method.
		"""
		input = self.__shared_storage.get_input()
		print(general.get_timestamp(f"Number of URLs to {'validate' if self.__validation_started else 'extract'}: {len(input)}"))
		print("Press CTRL + C to exit early - results will be saved, be patient")
		random.shuffle(input)
		for entry in input:
			yield scrapy.Request(
				url         = entry.url,
				headers     = self.__get_default_headers() | self.__shared_storage.get_headers(entry.key, with_cookies = False),
				cookies     = self.__shared_storage.get_cookies(entry.key),
				meta        = self.__get_metadata(entry),
				errback     = self.__error,
				callback    = self.__success,
				dont_filter = False
			)

	def __get_default_headers(self) -> dict[str, str]:
		"""
		Get default HTTP request headers.
		"""
		default_headers = {
			"User-Agent"               : self.__get_user_agent(),
			"Accept-Language"          : "en-US, *",
			"Accept"                   : "*/*",
			"Referer"                  : "https://www.google.com/",
			"Upgrade-Insecure-Requests": "1"
		}
		headers = {}
		for name, value in default_headers.items():
			if value:
				headers[name.lower()] = value
		return headers

	def __get_user_agent(self):
		"""
		Get a [random] user agent.\n
		Returns an empty string if there are no user agents.
		"""
		user_agent = ""
		if self.__user_agents_len > 0:
			user_agent = self.__user_agents[random.randint(0, self.__user_agents_len - 1)]
		return user_agent

	def __get_metadata(self, entry: input.InputGrouped) -> dict[str, typing.Any]:
		"""
		Get Scrapy's request metadata.
		"""
		# --------------------------------
		if self.__validation_started:
			self.__playwright, self.__playwright_wait = self.__shared_storage.get_playwright(entry.key)
		# --------------------------------
		self.__context += 1
		tmp                                = {}
		tmp["entry"                      ] = entry                  # custom attribute
		tmp["playwright_wait"            ] = self.__playwright_wait # custom attribute
		tmp["playwright"                 ] = self.__playwright
		tmp["playwright_context"         ] = str(self.__context)
		tmp["playwright_include_page"    ] = self.__playwright
		tmp["playwright_context_kwargs"  ] = {}
		tmp["playwright_context_kwargs"  ]["ignore_https_errors"] = True
		tmp["playwright_context_kwargs"  ]["java_script_enabled"] = True
		tmp["playwright_context_kwargs"  ]["accept_downloads"   ] = False
		tmp["playwright_context_kwargs"  ]["bypass_csp"         ] = False
		tmp["playwright_page_goto_kwargs"] = {"wait_until": "load"}
		tmp["proxy"                      ] = self.__proxy
		tmp["cookiejar"                  ] = self.__context
		tmp["dont_merge_cookies"         ] = False
		return tmp

	# ------------------------------------

	async def __error(self, failure: typing.Any):
		"""
		HTTP request error callback.
		"""
		entry      = failure.request.meta["entry"     ]
		playwright = failure.request.meta["playwright"]
		status     = failure.value.response.status if failure.check(scrapy.spidermiddlewares.httperror.HttpError) else 0
		error      = str(failure.value).splitlines()[0]
		if playwright:
			page = failure.request.meta["playwright_page"]
			if any(err in error for err in ["net::ERR_ABORTED", "net::ERR_CONNECTION_RESET"]):
				self.__print_fallback(playwright, status, entry.url)
				content, status, error = await self.__playwright_fallback(page, entry)
			await page.close()
			await page.context.close()
		if error:
			self.__append_error(entry, playwright, status, error)
		else:
			self.__append_success(entry, playwright, status, content)

	async def __playwright_fallback(self, page: typing.Any, entry: input.InputGrouped) -> tuple[str, int, str]:
		"""
		Fallback from 'Page.goto()' to 'APIRequestContext.get()'.
		"""
		content  = ""
		status   = 0
		error    = ""
		response = None
		try:
			response = await page.request.get(
				url                 = entry.url,
				headers             = self.__get_default_headers() | self.__shared_storage.get_headers(entry.key, with_cookies = True),
				ignore_https_errors = True,
				timeout             = self.__request_timeout * 1000,
				max_retries         = 0,
				max_redirects       = 10
			)
			status = response.status
			content, error = general.decode(await response.body())
		except (PlaywrightError, PlaywrightTimeoutError) as ex:
			error = str(ex).splitlines()[0]
		finally:
			if response:
				await response.dispose()
		return content, status, error

	def __append_error(self, entry: input.InputGrouped, playwright: bool, status: int, error: str):
		"""
		Append to the error list and print an error message.
		"""
		res = result.Result(entry.url, entry.files)
		self.__shared_storage.append_error(res)
		self.__print_error(playwright, status, entry.url, error)

	# ------------------------------------

	async def __success(self, response: typing.Any):
		"""
		HTTP request success callback.
		"""
		entry      = response.request.meta["entry"     ]
		playwright = response.request.meta["playwright"]
		content    = ""
		error      = ""
		if playwright:
			page = response.request.meta["playwright_page"]
			wait = response.request.meta["playwright_wait"]
			if wait > 0:
				await asyncio.sleep(wait)
			content = await page.content()
			await page.close()
			await page.context.close()
		elif hasattr(response, "text"):
			content = response.text
		else:
			content, error = general.decode(response.body)
		if url.normalize(entry.url) != response.url:
			self.__print_redirected(playwright, response.status, entry.url, response.url)
		if error:
			self.__append_error(entry, playwright, response.status, error)
		else:
			self.__append_success(entry, playwright, response.status, content)

	def __append_success(self, entry: input.InputGrouped, playwright: bool, status: int, content: str):
		"""
		Append to the success list and print an error message.
		"""
		res = result.Result(entry.url, entry.files)
		res.results = self.__shared_storage.parse_response(content, entry.key)
		if res.results:
			self.__shared_storage.append_success(res)
			self.__print_success(playwright, status, entry.url)
		else:
			self.__print_success_no_results(playwright, status, entry.url)

	# ------------------------------------

	def __print_fallback(self, playwright: bool, status: int, url: str):
		"""
		Print fallback.
		"""
		if self.__debug:
			if status:
				url = f"{status} {url}"
			general.print_cyan(f"[ FALLBACK ] PW:{int(playwright)} | {url} -> Page.goto() to APIRequestContext.get()")

	def __print_error(self, playwright: bool, status: int, url: str, message: str):
		"""
		Print error.
		"""
		if self.__debug:
			if status:
				url = f"{status} {url}"
			general.print_red(f"[ ERROR ] PW:{int(playwright)} | {url} -> {message}")

	def __print_redirected(self, playwright: bool, status: int, request_url: str, response_url: str):
		"""
		Print redirected.
		"""
		if self.__debug:
			general.print_yellow(f"[ REDIRECTED ] PW:{int(playwright)} | {request_url} -> {status} {response_url}")

	def __print_success(self, playwright: bool, status: int, url: str):
		"""
		Print success.
		"""
		if self.__debug:
			general.print_green(f"[ {'VALIDATED'if self.__validation_started else 'EXTRACTED'} ] PW:{int(playwright)} | {status} {url}")

	def __print_success_no_results(self, playwright: bool, status: int, url: str):
		"""
		Print success with no results.
		"""
		if self.__debug:
			general.print_magenta(f"[ NO MATCH ] PW:{int(playwright)} | {status} {url}")

# ----------------------------------------

class ChadExtractor:

	def __init__(
		self,
		shared_storage            : storage.Shared,
		playwright                : bool,
		playwright_wait           : float,
		concurrent_requests       : int,
		concurrent_requests_domain: int,
		sleep                     : float,
		random_sleep              : bool,
		auto_throttle             : float,
		retries                   : int,
		request_timeout           : float,
		user_agents               : list[str],
		proxy                     : str,
		debug                     : bool
	):
		"""
		Class for managing Scrapy's runner.
		"""
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
		self.__headless_browser           = True
		self.__browser_type               = "chromium" # Playwright's headless browser
		self.__handle_sigint              = False

	def __page_block(self, request: typing.Any):
		"""
		Types of content to block while using Playwright's headless browser.
		"""
		return request.resource_type in ["fetch", "stylesheet", "image", "ping", "font", "media", "imageset", "beacon", "csp_report", "object", "texttrack", "manifest"]

	def __run(self):
		"""
		Configure the settings and run the Chad Extractor spider.
		"""
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
		settings["REDIRECT_ENABLED"              ] = True
		settings["REDIRECT_MAX_TIMES"            ] = 10
		# --------------------------------
		settings["ROBOTSTXT_OBEY"                      ] = False
		settings["TELNETCONSOLE_ENABLED"               ] = False
		settings["LOG_ENABLED"                         ] = False
		settings["REQUEST_FINGERPRINTER_IMPLEMENTATION"] = "2.7"
		# --------------------------------
		if self.__shared_storage.is_validation_started():
			self.__playwright, self.__playwright_wait = self.__shared_storage.require_playwright()
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
		crawler.crawl(ChadExtractorSpider, self.__shared_storage, self.__playwright, self.__playwright_wait, self.__request_timeout, self.__user_agents, self.__proxy, self.__debug); crawler.start(); crawler.join()

	def run(self):
		"""
		Run Scrapy's spider.
		"""
		process = multiprocessing.Process(target = self.__run)
		try:
			process.start()
			process.join()
		except KeyboardInterrupt:
			process.terminate()
			process.join()
		return self.__shared_storage.has_success()
