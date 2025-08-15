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


def scrape_groups_wcy(url):
    logs = []
    
    def log_scrape_groups():
        groups = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ])
            try:
                log_entry("Browser launched (chromium, headless=True).", logs)
                page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")
                
                log_entry(f"Navigating to URL: {url}", logs)
                t0 = time.monotonic()
                resp = page.goto(url, timeout=20000)
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

        soup = BeautifulSoup(html, "html.parser")
        log_entry("Parsing HTML... Done.", logs)

        options = soup.find_all("option")
        log_entry(f"Found pagination element: {len(options)} options.", logs)
        
        for option in options:
                group = option.text.strip()

                if group and "- Wybierz grupę -" not in group:
                    group = group.rstrip(".")
                    groups.append(group)

        log_entry(f"Founding groups... Done.", logs)

        return groups

    groups = log("Scraping WCY groups names... ", log_scrape_groups)
    print(f"{OK} Scraped {len(groups)} WCY groups.")

    return groups


def save_to_file(groups):
    filename = os.path.join(GROUPS_DIR, "wcy.txt")

    if not os.path.exists(filename):
        print(f"Created a new db file for WCY groups: '{os.path.abspath(filename)}'")
    else:
        print(f"Using existing db file for WCY groups: '{os.path.abspath(filename)}'")

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
            f.write("# WCY Groups list\n")
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
        new_count, total_count = log("Saving WCY groups to file... ", save_log)

        if new_count > 0:
            print(f"{OK} Summary: Saved {new_count} WCY groups (marked with [NEW]) in '{os.path.abspath(filename)}'.")

        else:
            print(f"{OK} Summary: No new WCY groups found since last run.")

        print(f"[INFO]: Total WCY groups in '{os.path.abspath(filename)}' ({total_count})")

    except Exception as e:
        print(f"{E} {e}")


if __name__ == "__main__":

    start_time = time.time()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Start of WCY groups scraper:")

    url, description = load_url_from_config(key="wcy_groups", url_type="url")
    test_connection_with_monitoring(url, description)

    try:
        groups = scrape_groups_wcy(url)

        if groups:
            save_to_file(groups)

        else:
            print(f"{E} No data to save.")

    except Exception as e:
        print(f"{E} {e}")

    duration = time.time() - start_time

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WCY groups scraper finished  |  duration: {duration:.2f}s")