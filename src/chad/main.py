#!/usr/bin/env python3

from .utils import chad, config, validate

import datetime

# ----------------------------------------

class Stopwatch:

	def __init__(self):
		self.__start = datetime.datetime.now()

	def stop(self):
		self.__end = datetime.datetime.now()
		print(f"Script has finished in {self.__end - self.__start}")

stopwatch = Stopwatch()

# ----------------------------------------

def main():
	success, args = validate.Validate().validate_args()
	if success:
		config.banner()
		tool = chad.Chad(
			args.queries,
			args.site,
			args.time,
			args.total_results,
			args.page_results,
			args.minimum_queries,
			args.maximum_queries,
			args.minimum_pages,
			args.maximum_pages,
			args.user_agents,
			args.proxies,
			not args.no_sleep_on_start,
			args.debug
		)
		if tool.prepare() and tool.run():
			if args.directory:
				tool.download_files(args.threads, args.directory)
			if args.out:
				tool.save(args.out)
		stopwatch.stop()

if __name__ == "__main__":
	main()
