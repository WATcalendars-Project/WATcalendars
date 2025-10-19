import os
import sys
import time
import json
import asyncio
from datetime import datetime

from watcalendars import GROUPS_DIR, SCHEDULES_DIR
from watcalendars.utils.logutils import OK, ERROR, SUCCESS, WARNING
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wig import parse_wig_docx
from watcalendars.utils.downloader import download_schedule_file
from watcalendars.utils.writers.ics_writer import save_all_schedules
from watcalendars.utils.screenshot import save_docx_screenshot

GROUPS_FILE = os.path.join(GROUPS_DIR, "wig_groups_url.json")

async def async_main():
	start_time = time.time()
	print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WIG schedule (DOCX) parser:")
	print("")

	if not os.path.exists(GROUPS_FILE):
		print(f"{ERROR} Missing groups file: {GROUPS_FILE}")
		sys.exit(1)

	with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
		groups_map = json.load(f)

	pairs = list(groups_map.items())
	print(f"Groups to process: {len(pairs)}")

	downloads_dir = os.path.join(SCHEDULES_DIR, "wig_docx")
	os.makedirs(downloads_dir, exist_ok=True)

	# Directory for rendered screenshots of DOCX files
	wig_schedules_dir = os.path.join(SCHEDULES_DIR, "wig_schedules")
	os.makedirs(wig_schedules_dir, exist_ok=True)

	schedules = {}
	processed = 0

	for group_name, download_url in pairs:
		print(f"Downloading: {group_name}")
		path = download_schedule_file(download_url, downloads_dir, group_name)
		if not path or not os.path.exists(path):
			print(f"{WARNING} Skipping {group_name}: download failed")
			continue

		# Save a full-page PNG screenshot of the DOCX as a reference in wig_schedules
		png_path = os.path.join(wig_schedules_dir, f"{group_name}.png")
		if not save_docx_screenshot(path, png_path):
			print(f"{WARNING} Screenshot failed for {group_name}")
		lessons = parse_wig_docx(path)
		if not lessons:
			print(f"{WARNING} Skipping {group_name}: no lessons parsed")
			continue
		schedules[group_name] = lessons
		processed += 1

	if processed == 0:
		print(f"{ERROR} No WIG schedules parsed.")
		return

	writer_pairs = [(g, groups_map[g]) for g in schedules.keys()]
	save_all_schedules(schedules, writer_pairs, faculty_prefix="wig")

	duration = time.time() - start_time
	print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WIG schedule processing finished | duration: {duration:.2f}s")

def main():
	return asyncio.run(async_main())

if __name__ == "__main__":
	main()