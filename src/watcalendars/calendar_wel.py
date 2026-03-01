"""
WEL faculty schedule scraper using async scraper system.
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
from watcalendars.utils.parsers.schedule_parsers.schedule_parser_wel import parse_schedules
from watcalendars.utils.writers.ics_writer import save_all_schedules


def get_wel_group_urls(base_url):
    """Get list of (group_id, url) pairs for WEL groups."""
    groups = load_groups("wel")
    result = []
    for g in groups:
        url = base_url.format(group=quote(str(g), safe="*"))
        result.append((g, url))
    return result




async def main():
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start WEL schedule scraper:")
    print("")
    # Zbieramy plan z obu semestrów (zima + lato) do jednego ICS na grupę.
    combined_schedules = {}
    base_pairs = None  # Użyjemy par z pierwszego udanego sezonu jako listy grup do zapisu ICS.

    for season_key in ["url_zima", "url_lato"]:
        print(f"\n--- Processing season: {season_key} ---")

        # Sprawdzenie połączenia do indeksu dla danego semestru
        url, description = load_url_from_config(
            config_file=GROUPS_CONFIG, key="wel_groups", url_type=season_key
        )
        await asyncio.to_thread(test_connection_with_monitoring, url, description)
        print("")

        # Szablon URL do konkretnych grup dla tego semestru
        base_url, _ = load_url_from_config(
            config_file=SCHEDULES_CONFIG, key="wel_schedule", url_type=season_key
        )
        pairs = get_wel_group_urls(base_url)
        if not pairs:
            print(f"[ERROR] No groups found for season {season_key}.")
            continue

        if base_pairs is None:
            base_pairs = pairs

        print(f"Groups to scrape ({season_key}): {len(pairs)} (using async scraper for better performance)")
        print(f"URL: {base_url}")

        html_map = await scrape_urls_async(
            pairs,
            concurrency=10,
            progress_label=f"Scraping groups for wel ({season_key})")
        print("")

        season_schedules = parse_schedules(html_map)
        print("")

        # Dołączamy lekcje z tego semestru do wspólnej mapy
        for group_id, lessons in season_schedules.items():
            if not lessons:
                continue
            combined_schedules.setdefault(group_id, []).extend(lessons)

    if not combined_schedules or not base_pairs:
        print("[ERROR] No schedules collected for WEL (both seasons).")
        return

    save_all_schedules(combined_schedules, base_pairs, faculty_prefix="wel")
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

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WEL schedules scraper finished (duration: {HH_MM_SS})")


if __name__ == "__main__":
    asyncio.run(main())