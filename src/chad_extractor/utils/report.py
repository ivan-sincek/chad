#!/usr/bin/env python3

from . import config, file, general, jquery, result

import dataclasses

def save(results: result.Results, started_at: str, ended_at: str, out: str, verbose: bool, plaintext: bool):
	"""
	"""
	# ------------------------------------
	tmp = Report(started_at, ended_at)
	# ------------------------------------
	extracted       = results.results[result.Stage.EXTRACTION].success
	extracted_error = results.results[result.Stage.EXTRACTION].error
	validated       = results.results[result.Stage.VALIDATION].success
	validated_error = results.results[result.Stage.VALIDATION].error
	# ------------------------------------
	validated             = jquery.sort_by_url(validated)
	tmp.summary.validated = jquery.select_url(validated)
	# ------------------------------------
	extracted             = jquery.sort_by_file(extracted) if plaintext else jquery.sort_by_url(extracted)
	tmp.full              = extracted
	tmp.summary.extracted = jquery.select_results(tmp.full, sort = True)
	# ------------------------------------
	validated_error       = jquery.sort_by_url(validated_error)
	tmp.failed.validation = jquery.select_url(validated_error)
	# ------------------------------------
	extracted_error       = jquery.sort_by_url(extracted_error)
	tmp.failed.extraction = jquery.select_url(extracted_error)
	# ------------------------------------
	file.overwrite(get_primary(tmp, plaintext), out)
	# ------------------------------------
	if verbose:
		for path in jquery.select_file(extracted) if plaintext else jquery.select_files(extracted):
			# ----------------------------
			tmp = Report(started_at, ended_at)
			# ----------------------------
			tmp.summary.validated = jquery.select_url_by_file(validated, path)
			# ----------------------------
			tmp.full              = jquery.select_by_file(extracted, path) if plaintext else jquery.select_by_files(extracted, path)
			tmp.summary.extracted = jquery.select_results(tmp.full, sort = True)
			# ----------------------------
			tmp.failed.validation = jquery.select_url_by_file(validated_error, path)
			# ----------------------------
			tmp.failed.extraction = jquery.select_url_by_file(extracted_error, path)
			# ----------------------------
			file.write_silent(get_secondary(tmp, plaintext), path.rsplit(".", 1)[0] + config.REPORT_EXTENSION)

@dataclasses.dataclass
class ReportSummary:
	"""
	"""
	validated: list[str] = dataclasses.field(default_factory = list)
	extracted: list[str] = dataclasses.field(default_factory = list)

@dataclasses.dataclass
class ReportFailed:
	"""
	"""
	validation: list[str] = dataclasses.field(default_factory = list)
	extraction: list[str] = dataclasses.field(default_factory = list)

@dataclasses.dataclass
class Report:
	"""
	"""
	started_at: str           = ""
	ended_at  : str           = ""
	summary   : ReportSummary = dataclasses.field(default_factory = ReportSummary)
	failed    : ReportFailed  = dataclasses.field(default_factory = ReportFailed)
	full      : list          = dataclasses.field(default_factory = list)

def get_primary(report: Report, plaintext: bool):
	"""
	"""
	tmp = dataclasses.asdict(report)
	if not plaintext:
		for entry in tmp.get("full", []):
			del entry["files"]
	else:
		del tmp["failed"]["extraction"]
	return general.jdump(tmp)

def get_secondary(report: Report, plaintext: bool):
	"""
	"""
	tmp = dataclasses.asdict(report)
	if not plaintext:
		for entry in tmp.get("full", []):
			del entry["files"]
	else:
		del tmp["failed"]["extraction"]
		tmp["results"] = tmp["full"][0]["results"]
		del tmp["full"]
	return general.jdump(tmp)
