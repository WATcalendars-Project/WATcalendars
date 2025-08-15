import sys
import os
import time
import re
from datetime import datetime
from watcalendars import GROUPS_DIR
from watcalendars.utils.logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.url_loader import load_url_from_config
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def scrape_groups_wel(url):
    logs = []

    def log_scrape_groups():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'
            ])
            try:
                log_entry("Browser launched (chromium, headless=True).", logs)
                page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")

                log_entry(f"Navigating to URL: {url}", logs)
                t0 = time.monotonic()
                resp = page.goto(url, timeout=25_000)
                elapsed_ms = int((time.monotonic() - t0) * 1000)

                status = resp.status if resp else None
                ok = getattr(resp, "ok", None) if resp else None
                log_entry(f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}", logs)

                html = page.content()
                log_entry("Getting page content... Done.", logs)

            except PlaywrightTimeoutError as e:
                log_entry(f"Timeout navigating to {url}: {e}", logs)
                raise

            except Exception as e:
                log_entry(f"Unhandled error while scraping {url}: {e}", logs)
                raise

            finally:
                browser.close()
                log_entry("Closing browser... Done.", logs)

        if not html:
            log_entry(f"{E} No HTML retrieved.", logs)
            return []

        soup = BeautifulSoup(html, 'html.parser')
        log_entry("Parsing HTML content for WEL groups... Done.", logs)

        first_td = None

        for td in soup.find_all('td'):

            if td.get('valign', '').upper() == 'TOP':
                first_td = td
                log_entry(f"Found <td valign=TOP> element.", logs)
                break

        if not first_td:
            log_entry(f"{E} No <td valign=TOP> found.", logs)
            return []

        groups = set()

        for a in first_td.find_all('a', href=True):
            href = a['href']

            if not href.lower().endswith(('.htm', '.html')):
                continue
            
            base = href.rsplit('/', 1)[-1].split('?')[0].split('#')[0]
            base_no_ext = re.sub(r'\.(?:htm|html)$', '', base, flags=re.IGNORECASE).strip()
            
            if not base_no_ext:
                continue
            
            token = '_'.join(base_no_ext.split())
            groups.add(token)

        log_entry(f"Extracting group links from <td> element... Done.", logs)
        log_entry(f"Collected {len(groups)} groups.", logs)
        
        return sorted(groups)

    groups = log("Scraping WEL groups names...", log_scrape_groups)
    print(f"{OK} Scraped {len(groups)} WEL groups.")

    return groups


def save_to_file(groups):
    filename = os.path.join(GROUPS_DIR, "wel.txt")

    if not os.path.exists(filename):
        print(f"Created a new db file for WEL groups: '{os.path.abspath(filename)}'")
    else:
        print(f"Using existing db file for WEL groups: '{os.path.abspath(filename)}'")

    def save_log():
        logs = []
        current = set(groups)
        existing = set()

        if os.path.exists(filename):
            
            try:
                with open(filename, 'r', encoding="utf-8") as f:
                    for line in f:

                        if line.strip() and not line.startswith('#'):
                            existing.add(re.sub(r"\s+\[NEW\]$", "", line.strip()))

            except Exception:
                pass

        log_entry(f"Current groups to save: {len(current)}", logs)
        if existing:
            log_entry(f"Existing groups loaded: {len(existing)}", logs)
        new_groups = current - existing
        log_entry(f"New groups detected: {len(new_groups)}", logs)
        
        with open(filename, 'w', encoding='utf-8') as f:
            log_entry(f"Opening db file '{os.path.abspath(filename)}'... Done.", logs)
            f.write("# WEL Groups list\n")
            f.write(f"# Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total number of groups: {len(current)}\n")
            
            if new_groups:
                f.write(f"# New groups found in this run: {len(new_groups)}\n")

            f.write("\n")

            for g in sorted(current):
                marker = " [NEW]" if g in new_groups else ""
                f.write(f"{g}{marker}\n")
        
        log_entry(f"Writing header and metadata... Done.", logs)
        return len(new_groups), len(current)

    try:
        new_count, total_count = log("Saving WEL groups to file... ", save_log)
        
        if new_count > 0:
            print(f"{OK} Summary: Saved {new_count} WEL groups (marked with [NEW]) in '{os.path.abspath(filename)}'.")

        else:
            print(f"{OK} Summary: No new WEL groups found since last run.")

        print(f"[INFO]: Total WEL groups in '{os.path.abspath(filename)}' ({total_count})")

    except Exception as e:
        print(f"{E} {e}")


if __name__ == '__main__':

    start_time = time.time()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start of WEL groups scraper:")

    url, description = load_url_from_config(key="wel_groups", url_type="url_lato")
    test_connection_with_monitoring(url, description)

    print(f"Scraping from URL: {url}")

    try:
        groups = scrape_groups_wel(url)

        if groups:
            save_to_file(groups)

        else:
            print(f"{E} No data to save.")

    except Exception as e:
        print(f"{E} {e}")

    duration = time.time() - start_time

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WEL groups scraper finished  |  duration: {duration:.2f}s")