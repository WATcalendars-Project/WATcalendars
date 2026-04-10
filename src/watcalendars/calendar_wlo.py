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
from watcalendars.utils.async_scraper import scrape_urls_async, AsyncScraper
from watcalendars.utils.url_loader import load_url_from_config  
from watcalendars.utils.groups_loader import load_groups
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wlo import parse_schedules
from watcalendars.utils.writers.ics_writer import save_all_schedules, normalize_lesson_data
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS
from watcalendars.utils.config import get_current_semester

def get_wlo_group_urls(base_url: str):
    """Generate WLO group URLs for given base_url template."""
    groups = load_groups("wlo")
    result = []

    for g in groups:
        url = base_url.format(group=quote(str(g), safe="*"))
        result.append((g, url))

    return result


async def main():
    """Main async function for WLO scraper."""
    start_time = time.time()
    print(f"\n------[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WLO schedule scraper:------\n")
    
    current_month = datetime.now().month
    current_semester = get_current_semester()
    season = f"url_{current_semester}"
    season_suffix = f"_{current_semester}"

    print(f"{INFO} Current month is: {current_month}. According to the schedule, the selected semester is: {current_semester.upper()}")
    print(f"Processing season: {season}...")
    print("")

    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG,
        key="wlo_groups",
        url_type=season
    )

    await asyncio.to_thread(test_connection_with_monitoring, url, description)
    print("")

    base_url, description = load_url_from_config(
        config_file=SCHEDULES_CONFIG,
        key="wlo_schedule",
        url_type=season
    )
    pairs = get_wlo_group_urls(base_url)
    if not pairs:
        print(f"{ERROR} No groups found.")
        sys.exit(1)

    print(f"{INFO} Groups to scrape: {len(pairs)} (using async scraper for better performance)")
    print(f"URL: {base_url}")

    async def custom_wlo_fetch(page, identifier, url):
        await asyncio.sleep(2) # Natural delay to prevent WAF flagging
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Disable navigation timeout exceptions which cause NS_ERROR_ABORT
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                
                # Active waiting logic for Incapsula redirect
                is_incapsula = True
                html = ""
                for wait_step in range(15):  # Wait up to 30 seconds for WAF to solve
                    await asyncio.sleep(2)
                    try:
                        html = await page.content()
                    except Exception:
                        continue
                        
                    if len(html) > 2000 and "Incapsula" not in html:
                        is_incapsula = False
                        break
                        
                if is_incapsula:
                    print(f"{WARNING} Group {identifier} intercepted by Incapsula (bytes {len(html)}). Retrying {attempt+1}/{max_retries}...")
                    continue
                
                if len(html) < 1000:
                    print(f"{WARNING} Extracted HTML for {identifier} is too small (bytes {len(html)}). Retrying {attempt+1}/{max_retries}...")
                    continue

                print(f"{OK} Scraping {identifier} completed. (bytes {len(html)})")
                return html
            except Exception as e:
                print(f"{WARNING} Error for {identifier} (retry {attempt+1}/{max_retries}): {e}")
                await asyncio.sleep(3)
        print(f"{ERROR} Failed to scrape {identifier} after {max_retries} attempts.")
        return None

    # Use extremely low concurrency (1) to prevent Incapsula bans
    scraper = AsyncScraper(concurrency=1)
    html_results = await scraper.scrape_with_custom_logic(
        pairs,
        custom_wlo_fetch,
        progress_label=f"Scraping groups for wlo ({season})"
    )
    print("")

    schedules = parse_schedules(html_results)
    print("")

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
