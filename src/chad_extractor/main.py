#!/usr/bin/env python3

from .utils import config, extractor, report, result, storage, validate

import datetime

# ----------------------------------------

class Stopwatch:

	def __init__(self):
		self.__format = "%Y-%m-%d %H:%M:%S"
		self.__start  = datetime.datetime.now()

	def stop(self):
		self.__end = datetime.datetime.now()
		print(f"Script has finished in {self.__end - self.__start}")

	def get_start(self):
		return self.__start.strftime(self.__format)

	def get_end(self):
		return self.__end.strftime(self.__format)

stopwatch = Stopwatch()

# ----------------------------------------

def main():
	success, args = validate.Validate().validate_args()
	if success:
		config.banner()
		results = None
		storage.MyManager.register("Shared", storage.Shared)
		with storage.MyManager() as manager:
			shared_storage: storage.Shared = manager.Shared(
				args.template,
				args.results,
				args.plaintext,
				args.excludes,
				args.debug
			)
			tool = extractor.ChadExtractor(
				shared_storage,
				args.playwright,
				args.playwright_wait,
				args.concurrent_requests,
				args.concurrent_requests_domain,
				args.sleep,
				args.random_sleep,
				args.auto_throttle,
				args.retries,
				args.request_timeout,
				args.user_agents,
				args.proxy,
				args.debug
			)
			if not shared_storage.parse_template():
				print("No extraction details were found in the template")
			elif not shared_storage.parse_input():
				print("No data was extracted" if args.plaintext else "No Chad results are suitable for extraction")
			elif not args.plaintext and not tool.run():
				print("No data was extracted")
			else:
				shared_storage.start_validation()
				if not shared_storage.parse_template():
					print("No validation details were found in the template")
				elif not shared_storage.parse_input():
					print("No extracted data is suitable for validation")
				elif not tool.run():
					print("No extracted data matched the validation criteria")
			results = shared_storage.get_results()
		stopwatch.stop()
		if results.results[result.Stage.EXTRACTION].success:
			report.save(
				results,
				stopwatch.get_start(),
				stopwatch.get_end(),
				args.out,
				args.verbose,
				args.plaintext
			)

if __name__ == "__main__":
	main()
