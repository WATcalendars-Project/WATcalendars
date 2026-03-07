import os
import time
import re
from datetime import datetime

from watcalendars import DB_DIR, GROUPS_DIR, GROUPS_CONFIG, SCHEDULES_CONFIG
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.scraper import scrape_html
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from watcalendars.utils.parsers.groups_parsers.groups_parser_wml import parse_wml_groups
from watcalendars.utils.writers.groups_url_writer import save_groups_json
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS

if __name__ == '__main__':
    start_time = time.time()
    print(f"\n------[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start of WML groups scraper:------\n")

    url, description = load_url_from_config(
        config_file=GROUPS_CONFIG,
        key="wml_groups",
        url_type="url"
    )
    test_connection_with_monitoring(url, description)
    print("")

    try:
        print(f"{INFO} Scraping groups from URL:\n{url}")
        html, logs = scrape_html(url)
        print("")
        
        print(f"{INFO} Parsing {len(html)} bytes of HTML:")

        # Some faculties embed an index.xml (with actual group links) inside the page.
        # Try to find a link to index.xml and fetch it (like WLO does).
        index_xml_url = None
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all(['a', 'iframe'], href=True):
                href = a.get('href') or a.get('src')
                if href and 'index.xml' in href:
                    index_xml_url = urljoin(url, href)
                    break
        except Exception:
            index_xml_url = None

        if index_xml_url:
            xml_html, xml_logs = scrape_html(index_xml_url)
            print("")
            groups = parse_wml_groups(xml_html, logs)
        else:
            # As a last resort, check the scraper logs for a fetched index.xml URL
            found = False
            if logs:
                for entry in logs:
                    if isinstance(entry, str) and 'index.xml' in entry:
                        m = re.search(r'(https?://[^\s\]]*index\.xml)', entry)
                        if m:
                            index_xml_url = m.group(1)
                            found = True
                            break
            if found and index_xml_url:
                xml_html, xml_logs = scrape_html(index_xml_url)
                groups = parse_wml_groups(xml_html, logs)
            else:
                if 'index.xml' in html:
                    m = re.search(r'(https?://[^"\'\s>]+index\.xml)', html)
                    if not m:
                        m = re.search(r'["\']([^"\']*index\.xml)["\']', html)
                    if m:
                        index_xml_url = urljoin(url, m.group(1) if m.group(1).startswith('http') else m.group(1))
                        xml_html, xml_logs = scrape_html(index_xml_url)
                        groups = parse_wml_groups(xml_html, logs)
                    else:
                        groups = parse_wml_groups(html, logs)
                else:
                    groups = parse_wml_groups(html, logs)
        print(f"{SUCCESS} Collected {len(groups)} WML groups.")
        print("")

        if groups:
            save_groups_json(
                groups=groups,
                groups_dir=GROUPS_DIR,
                filename_prefix="wml",
                url_config_path=SCHEDULES_CONFIG,
                schedule_key="wml_schedule",
                schedule_type="url"
            )
        else:
            print(f"{ERROR} No data to save.")
    except Exception as e:
        print(f"{ERROR} {e}")
    print("")

    duration = time.time() - start_time
    print(f"{INFO} {datetime.now().strftime('%Y-%m-%d %H:%M')} WML groups scraper finished  |  duration: {duration:.2f}s")
    print("")