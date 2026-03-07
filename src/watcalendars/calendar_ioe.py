"""
IOE faculty schedule scraper using async scraper system.
"""
import os
import sys
import time
import asyncio
from datetime import datetime
from urllib.parse import quote

from watcalendars import DB_DIR, GROUPS_CONFIG, SCHEDULES_CONFIG
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.groups_loader import load_groups
from watcalendars.utils.async_scraper import scrape_urls_async
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_ioe import parse_schedules
from watcalendars.utils.writers.ics_writer import save_all_schedules
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS
from watcalendars.utils.config import get_current_semester


def get_ioe_group_urls(base_url):
    groups = load_groups("ioe")
    return [(g, base_url.format(group=quote(str(g), safe="*"))) for g in groups]


async def main():
    start_time = time.time()
    print(f"\n------[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start IOE schedule scraper:------\n")

    current_month = datetime.now().month
    current_semester = get_current_semester()
    season = f"url_{current_semester}"
    season_suffix = f"_{current_semester}"

    print(f"{INFO} Current month is: {current_month}. According to the schedule, the selected semester is: {current_semester.upper()}")
    print(f"Processing season: {season}...")
    print("")

    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG,
        key="ioe_groups",
        url_type=season
    )

    await asyncio.to_thread(test_connection_with_monitoring, url, description)
    print("")

    base_url, description = load_url_from_config(
        config_file=SCHEDULES_CONFIG,
        key="ioe_schedule",
        url_type=season
    )

    pairs = get_ioe_group_urls(base_url)
    if not pairs:
        print(f"{ERROR} No groups found.")
        sys.exit(1)

    print(f"{INFO} Groups to scrape: {len(pairs)} (using async scraper for better performance)")
    print(f"URL: {base_url}")

    html_map = await scrape_urls_async(
        pairs, 
        concurrency=10, 
        progress_label="Scraping groups for ioe")
    print("")

    schedules = parse_schedules(html_map)
    print("")

    save_all_schedules(schedules, pairs, faculty_prefix="ioe")
    print("")

    duration = time.time() - start_time
    total_seconds = int(duration)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        HH_MM_SS = f"{hours:02}h{minutes:02}m{seconds:02}s"
    elif minutes > 0:
        HH_MM_SS = f"{minutes:02}m{seconds:02}s"
    else:
        HH_MM_SS = f"{seconds:02}s"

    print(f"{INFO} [{datetime.now().strftime('%Y-%m-%d %H:%M')}] IOE schedules scraper finished (duration: {HH_MM_SS})")
    print("")

if __name__ == "__main__":
    asyncio.run(main())