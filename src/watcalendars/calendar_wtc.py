"""
WTC department schedule scraper using async scraper system.
"""

import time
import asyncio
from datetime import datetime

from watcalendars import DB_DIR, GROUPS_CONFIG, SCHEDULES_CONFIG
from watcalendars.utils.async_scraper import scrape_urls_async
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wtc import parse_schedules
from watcalendars.utils.writers.ics_writer import save_all_schedules, normalize_lesson_data
from watcalendars.utils.writers.screenshot_writer import save_screenshot_async
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.groups_loader import load_groups
from urllib.parse import quote


def get_wtc_group_urls():
    """Load WTC groups and generate URLs for scraping."""
    try:
        groups = load_groups("wtc")
    except Exception as e:
        print(f"Error loading WTC groups: {e}")
        return []

    base_url, _ = load_url_from_config(
        config_file=SCHEDULES_CONFIG, key="wtc_schedule", url_type="url"
    )
    
    result = []
    for group in groups:
        url = base_url.format(group=quote(str(group), safe="*"))
        result.append((group, url))
    
    return result


async def screenshot_callback(page, identifier):
    """Save screenshot for a group."""
    await save_screenshot_async(page, identifier, "wtc")


async def main():
    """Main async function for WTC schedule scraping."""
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WTC schedule scraper:")
    print("")

    print("Check connection:")
    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG, key="wtc_groups", url_type="url"
    )
    print(f"URL: {url}")
    test_connection_with_monitoring(url, description)
    print("")
    
    pairs = get_wtc_group_urls()
    if not pairs:
        print("==> ERROR: No WTC groups found.")
        return

    print("Scraping group URLs:")
    base_url, _ = load_url_from_config(
        config_file=SCHEDULES_CONFIG, key="wtc_schedule", url_type="url"
    )
    print(f"Groups to scrape: {len(pairs)} (using async scraper for better performance)")
    print(f"URL: {base_url}")
    
    html_results = await scrape_urls_async(
        pairs, 
        progress_label="Scraping groups for wtc groups for groups for",
        save_screenshots=True,
        screenshot_callback=screenshot_callback
    )
    print("")
    
    schedules = parse_schedules(html_results)
    print("")
    
    for group_id in schedules:
        if schedules[group_id]:
            schedules[group_id] = [normalize_lesson_data(lesson) for lesson in schedules[group_id]]

    save_all_schedules(schedules, pairs, faculty_prefix="wtc")
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
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WTC schedules scraper finished (duration: {HH_MM_SS})")


if __name__ == "__main__":
    asyncio.run(main())
