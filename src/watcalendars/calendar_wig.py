import os
import sys
import time
import json
import asyncio
from datetime import datetime

from watcalendars import GROUPS_DIR, SCHEDULES_DIR
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wig import parse_wig_docx
from watcalendars.utils.downloader import download_schedule_file
from watcalendars.utils.writers.ics_writer import save_all_schedules

GROUPS_FILE = os.path.join(GROUPS_DIR, "wig_groups_url.json")
GROUPS_SUBDIR = os.path.join(GROUPS_DIR, "wig_groups_url")


def _load_wig_groups_map():
	"""Load WIG groups -> URL map from db/groups_url.

	Najpierw próbuje starego pliku db/groups_url/wig_groups_url.json,
	a jeżeli go nie ma, składa mapę ze wszystkich plików JSON w
	db/groups_url/wig_groups_url/.
	"""
	groups_map = {}

	# 1) Stary, płaski plik (jeśli istnieje)
	if os.path.exists(GROUPS_FILE):
		with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
			groups_map = json.load(f)
		return groups_map

	# 2) Nowa struktura: wiele plików w katalogu wig_groups_url/
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
			print(f"[WARNING] Failed to load {path}: {e}")
			continue

		if not isinstance(data, dict):
			print(f"[WARNING] Unexpected JSON structure in {path} (expected object)")
			continue

		for group_name, url in data.items():
			# Jeśli grupa już istnieje i URL jest ten sam – ignorujemy dubel.
			if group_name in groups_map:
				if groups_map[group_name] != url:
					print(
						f"[WARNING] Duplicate group '{group_name}' with different URLs;"
						f" keeping first, skipping from {name}"
					)
				continue
			groups_map[group_name] = url

	return groups_map

async def async_main():
	start_time = time.time()
	print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WIG schedule (DOCX) parser:")
	print("")

	try:
		groups_map = _load_wig_groups_map()
	except FileNotFoundError as e:
		print(f"[ERROR] {e}")
		sys.exit(1)

	if not groups_map:
		print(f"[ERROR] No WIG groups loaded from db/groups_url.")
		return

	pairs = list(groups_map.items())
	print(f"Groups to process: {len(pairs)}")

	downloads_dir = os.path.join(SCHEDULES_DIR, "wig_docx")
	os.makedirs(downloads_dir, exist_ok=True)
	schedules = {}
	processed = 0

	for group_name, download_url in pairs:
		print(f"Downloading: {group_name}")
		path = download_schedule_file(download_url, downloads_dir, group_name)
		if not path or not os.path.exists(path):
			print(f"[WARNING] Skipping {group_name}: download failed")
			continue
		lessons = parse_wig_docx(path)
		if not lessons:
			print(f"[WARNING] Skipping {group_name}: no lessons parsed")
			continue
		schedules[group_name] = lessons
		processed += 1

	if processed == 0:
		print(f"[ERROR] No WIG schedules parsed.")
		return

	writer_pairs = [(g, groups_map[g]) for g in schedules.keys()]
	save_all_schedules(schedules, writer_pairs, faculty_prefix="wig")

	duration = time.time() - start_time
	print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WIG schedule processing finished | duration: {duration:.2f}s")

def main():
	return asyncio.run(async_main())

if __name__ == "__main__":
	main()