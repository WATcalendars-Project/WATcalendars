"""
WML faculty schedule scraper using async scraper system.
"""
import os
import sys
import time
import asyncio
from datetime import datetime
from urllib.parse import quote

from watcalendars import DB_DIR, GROUPS_CONFIG, SCHEDULES_CONFIG
from watcalendars.calendar_wel import get_wel_group_urls
from watcalendars.utils.logutils import OK, ERROR, SUCCESS, log, log_entry
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.groups_loader import load_groups
from watcalendars.utils.async_scraper import scrape_urls_async
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wml import parse_schedules
from watcalendars.utils.writers.ics_writer import save_all_schedules
from watcalendars.utils.writers.screenshot_writer import save_screenshot_async


def get_wml_group_urls(base_url):
    """Get list of (group_id, url) pairs for WML groups."""
    groups = load_groups("wml")
    result = []
    for g in groups:
        url = base_url.format(group=quote(str(g), safe="*"))
        result.append((g, url))
    return result


async def screenshot_callback(page, group_name):
    """Callback function to save screenshots for WML groups"""
    await save_screenshot_async(page, group_name, "wml")


async def main():
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WML schedule scraper:")
    print("")

    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG, key="wml_groups", url_type="url"
    )
    test_connection_with_monitoring(url, description)
    print("")

    base_url, _ = load_url_from_config(
        config_file=SCHEDULES_CONFIG, key="wml_schedule", url_type="url"
    )
    pairs = get_wml_group_urls(base_url)
    if not pairs:
        print(f"{ERROR} No groups found.")
        sys.exit(1)

    print(f"Groups to scrape: {len(pairs)} (using async scraper for better performance)")
    print(f"URL: {base_url}")
    
    html_map = await scrape_urls_async(
        pairs, 
        concurrency=10, 
        progress_label="Scraping groups for wml",
        save_screenshots=True,
        screenshot_callback=screenshot_callback
    )
    print("")

    schedules = parse_schedules(html_map)
    print("")

    save_all_schedules(schedules, pairs, faculty_prefix="wml")
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

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WML schedules scraper finished (duration: {HH_MM_SS})")


if __name__ == "__main__":
    asyncio.run(main())