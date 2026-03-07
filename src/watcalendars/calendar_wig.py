import os
import sys
import time
import json
import asyncio
from datetime import datetime

from watcalendars import GROUPS_CONFIG, GROUPS_DIR, SCHEDULES_DIR
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wig import parse_wig_docx
from watcalendars.utils.downloader import download_schedule_file
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.writers.ics_writer import save_all_schedules
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS

GROUPS_FILE = os.path.join(GROUPS_DIR, "wig_groups_url.json")
GROUPS_SUBDIR = os.path.join(GROUPS_DIR, "wig_groups_url")


def _load_wig_groups_map():
	"""Load WIG groups -> URL map from db/groups_url.

	Najpierw próbuje starego pliku db/groups_url/wig_groups_url.json,
	a jeżeli go nie ma, składa mapę ze wszystkich plików JSON w
	db/groups_url/wig_groups_url/.
	"""
	groups_map = {}

	if os.path.exists(GROUPS_FILE):
		with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
			groups_map = json.load(f)
		return groups_map

	if not os.path.isdir(GROUPS_SUBDIR):
		raise FileNotFoundError(
			f"No WIG groups data found. Expected {GROUPS_FILE} or directory {GROUPS_SUBDIR}"
		)

	json_files = [
		f for f in os.listdir(GROUPS_SUBDIR)
		if f.lower().endswith('.json')
	]
	if not json_files:
		raise FileNotFoundError(
			f"No JSON files found in {GROUPS_SUBDIR} for WIG groups"
		)

	for name in sorted(json_files):
		path = os.path.join(GROUPS_SUBDIR, name)
		try:
			with open(path, 'r', encoding='utf-8') as f:
				data = json.load(f)
		except Exception as e:
			print(f"{WARNING} Failed to load {path}: {e}")
			continue

		if not isinstance(data, dict):
			print(f"{WARNING} Unexpected JSON structure in {path} (expected object)")
			continue

		for group_name, url in data.items():
			if group_name in groups_map:
				if groups_map[group_name] != url:
					print(
						f"{WARNING} Duplicate group '{group_name}' with different URLs;"
						f" keeping first, skipping from {name}"
					)
				continue
			groups_map[group_name] = url

	return groups_map

async def async_main():
	start_time = time.time()
	print(f"\n------[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WIG schedule (DOCX) downloader and parser:------\n")

	url, description = load_url_from_config(
		config_file=GROUPS_CONFIG, key="wig_groups", url_type="url_podkategoria"
	)
	await asyncio.to_thread(test_connection_with_monitoring, url, description)
	print("")

	try:
		groups_map = _load_wig_groups_map()
	except FileNotFoundError as e:
		print(f"{ERROR} {e}")
		sys.exit(1)

	if not groups_map:
		print(f"{ERROR} No WIG groups loaded from db/groups_url.")
		return

	pairs = list(groups_map.items())
	print(f"{INFO} Groups to process: {len(pairs)}")

	downloads_dir = os.path.join(GROUPS_DIR, "wig_groups_url", "wig_docx")
	os.makedirs(downloads_dir, exist_ok=True)
	schedules = {}
	processed = 0

	for group_name, download_url in pairs:
		print(f"Downloading {group_name}...")
		path = download_schedule_file(download_url, downloads_dir, group_name)
		if not path or not os.path.exists(path):
			print(f"{WARNING} Skipping {group_name}: download failed")
			continue
		lessons = parse_wig_docx(path)
		if not lessons:
			print(f"{WARNING} Skipping {group_name}: no lessons parsed")
			continue
		schedules[group_name] = lessons
		processed += 1

	if processed == 0:
		print(f"{ERROR} No WIG schedules parsed.")
		return
	print("")

	writer_pairs = [(g, groups_map[g]) for g in schedules.keys()]
	save_all_schedules(schedules, writer_pairs, faculty_prefix="wig")
	print("")

	duration = time.time() - start_time
	print(f"{INFO} WIG schedule processing finished | duration: {duration:.2f}s")
	print("")

def main():
	return asyncio.run(async_main())

if __name__ == "__main__":
	main()