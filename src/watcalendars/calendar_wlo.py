"""
WLO department schedule scraper using async scraper system.
"""

import sys
import os
import time
import asyncio
from datetime import datetime
from urllib.parse import quote

from watcalendars import DB_DIR, GROUPS_CONFIG, SCHEDULES_CONFIG
from watcalendars.utils.async_scraper import scrape_urls_async
from watcalendars.utils.logutils import OK, ERROR as E
from watcalendars.utils.url_loader import load_url_from_config  
from watcalendars.utils.groups_loader import load_groups
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wlo import parse_schedules
from watcalendars.utils.writers.ics_writer import save_all_schedules, normalize_lesson_data
from watcalendars.utils.writers.screenshot_writer import save_screenshot_async
from watcalendars.utils.connection import test_connection_with_monitoring


def get_wlo_group_urls():
    """Generate WLO group URLs."""
    groups = load_groups("wlo")
    base_url, _ = load_url_from_config(
        config_file=SCHEDULES_CONFIG, key="wlo_schedule", url_type="url_zima"
    )
    result = []
    
    for g in groups:
        url = base_url.format(group=quote(str(g), safe="*"))
        result.append((g, url))
    
    return result


async def screenshot_callback(page, group_name):
    """Callback function to save screenshots for WLO groups"""
    await save_screenshot_async(page, group_name, "wlo")


async def main():
    """Main async function for WLO scraper."""
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WLO schedule scraper:")
    print("")

    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG, key="wlo_groups", url_type="url_zima"
    )
    test_connection_with_monitoring(url, description)
    print("")
    
    pairs = get_wlo_group_urls()
    if not pairs:
        print(f"{E} No groups found.")
        sys.exit(1)
    
    base_url, _ = load_url_from_config(
        config_file=SCHEDULES_CONFIG, key="wlo_schedule", url_type="url_zima"
    )
    print(f"Groups to scrape: {len(pairs)} (using async scraper for better performance)")
    print(f"URL: {base_url}")
    
    url_pairs = [(group_id, url) for group_id, url in pairs]
    
    html_results = await scrape_urls_async(
        url_pairs=url_pairs,
        progress_label="Scraping groups for wlo groups for",
        save_screenshots=True,
        screenshot_callback=screenshot_callback,
        concurrency=10
    )
    print("")
    
    schedules = parse_schedules(html_results)
    print("")
    
    for group_id in schedules:
        if schedules[group_id]:
            schedules[group_id] = [normalize_lesson_data(lesson) for lesson in schedules[group_id]]
    
    save_all_schedules(schedules, pairs, faculty_prefix="wlo")
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
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WLO schedules scraper finished (duration: {HH_MM_SS})")


if __name__ == "__main__":
    asyncio.run(main())
