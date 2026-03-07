import os
import time
from datetime import datetime

from watcalendars import DB_DIR, GROUPS_DIR, GROUPS_CONFIG, SCHEDULES_CONFIG
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.scraper import scrape_html
from watcalendars.utils.parsers.groups_parsers.groups_parser_wim import parse_wim_groups
from watcalendars.utils.writers.groups_url_writer import save_groups_json
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS
from watcalendars.utils.config import get_current_semester

if __name__ == '__main__':
    start_time = time.time()
    print(f"\n------[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start of WIM groups scraper:------\n")

    current_month = datetime.now().month
    current_semester = get_current_semester()
    season = f"url_{current_semester}"
    season_suffix = f"_{current_semester}"

    print(f"{INFO} Current month is: {current_month}. According to the schedule, the selected semester is: {current_semester.upper()}")
    print(f"Processing season: {season}...")
    print("")
        
    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG,
        key="wim_groups",
        url_type=season
    )
    test_connection_with_monitoring(url, description)
    print("")

    try:
        print(f"{INFO} Scraping groups from URL:\n{url}")
        html, logs = scrape_html(url)
        print("")

        print(f"{INFO} Parsing {len(html)} bytes of HTML:")
        groups = parse_wim_groups(html, logs)
        print(f"{SUCCESS} Collected {len(groups)} WIM groups for {season}.")
        print("")

        if groups:
            save_groups_json(
                groups=groups,
                groups_dir=GROUPS_DIR,
                filename_prefix="wim",
                url_config_path=SCHEDULES_CONFIG,
                schedule_key="wim_schedule",
                schedule_type=season,
                season_suffix=season_suffix
            )
        else:
            print(f"{ERROR} No data to save for {season}.")
    except Exception as e:
        print(f"{ERROR} during {season} processing: {e}")
    print("")

    duration = time.time() - start_time
    print(f"{INFO} {datetime.now().strftime('%Y-%m-%d %H:%M')} WIM groups scraper finished  |  duration: {duration:.2f}s")
    print("")