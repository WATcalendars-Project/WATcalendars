import os
import time
from datetime import datetime

from watcalendars import DB_DIR, GROUPS_DIR, GROUPS_CONFIG, SCHEDULES_CONFIG
from watcalendars.utils.logutils import OK, ERROR, SUCCESS
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.scraper import scrape_html
from watcalendars.utils.parsers.groups_parsers.groups_parser_wtc import parse_wtc_groups
from watcalendars.utils.writers.groups_url_writer import save_groups_json

if __name__ == '__main__':
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start of WTC groups scraper:")
    print("")

    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG,
        key="wtc_groups",
        url_type="url"
    )
    test_connection_with_monitoring(url, description)
    print("")

    try:
        print(f"Scraping groups from URL:\n{url}")
        html, logs = scrape_html(url)
        print("")
        
        print(f"Parsing {len(html)} bytes of HTML:")
        groups = parse_wtc_groups(html, logs)
        print(f"{SUCCESS} Collected {len(groups)} WTC groups.")
        print("")

        if groups:
            save_groups_json(
                groups=groups,
                groups_dir=GROUPS_DIR,
                filename_prefix="wtc",
                url_config_path=SCHEDULES_CONFIG,
                schedule_key="wtc_schedule",
                schedule_type="url"
            )
        else:
            print(f"{ERROR} No data to save.")
    except Exception as e:
        print(f"{ERROR} {e}")
    print("")

    duration = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WTC groups scraper finished  |  duration: {duration:.2f}s")