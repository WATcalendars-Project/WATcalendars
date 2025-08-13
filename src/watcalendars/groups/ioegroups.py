#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import re
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log
from url_loader import load_url_from_config
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Flexible pattern: allow existing IOE* plus generic 2-5 letters + 2 digits + trailing alphanum
GENERIC_GROUP_RE = re.compile(r'^[A-Z]{2,5}\d{2}[A-Z0-9]{2,}$')
LEGACY_PREFIX = 'IOE'

def is_group_candidate(token: str) -> bool:
    if not token or ' ' in token or len(token) > 40:
        return False
    if token.startswith(LEGACY_PREFIX):
        return True
    if GENERIC_GROUP_RE.match(token):
        return True
    return False


def scrape_groups_ioe(url):
    print(f"\n{INFO} Scrape IOE groups (flexible mode).")
    logs = []

    def log_scrape():
        groups_found = set()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'
            ])
            page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")
            page.goto(url, timeout=20000)
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, 'html.parser')

        # Strategy 1: links to individual schedules
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            if href.endswith('.htm') and 'Plany' in href and is_group_candidate(text):
                groups_found.add(text)

        # Strategy 2: plain text tokens
        for token in soup.stripped_strings:
            if is_group_candidate(token):
                groups_found.add(token)

        cleaned = {g.rstrip('.') for g in groups_found}
        log_entry(f"Extracted {len(cleaned)} raw group names", logs)
        return sorted(cleaned)

    groups = log("Scraping IOE groups list... ", log_scrape)
    print(f"{OK} Scraped {len(groups)} IOE groups (flexible).")
    return groups


def save_to_file(groups):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(script_dir, "..", "..", "..", "db", "groups")
    os.makedirs(db_dir, exist_ok=True)
    filename = os.path.join(db_dir, "ioe.txt")
    if not os.path.exists(filename):
        print(f"Created a new db file for IOE groups: '{os.path.abspath(filename)}'")
    else:
        print(f"Using existing db file for IOE groups: '{os.path.abspath(filename)}'")

    def save_log():
        existing_groups = set()
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            name = re.sub(r"\s+\[NEW\]$", "", line.strip())
                            existing_groups.add(name)
            except Exception:
                pass
        normalized = set(g.strip() for g in groups)
        new_groups = normalized - existing_groups
        all_groups = existing_groups | normalized
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('# IOE Groups list (flexible detection)\n')
            f.write(f"# Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total number of groups: {len(all_groups)}\n")
            if new_groups:
                f.write(f"# New groups found in this run: {len(new_groups)}\n")
            f.write('\n')
            for g in sorted(all_groups):
                marker = ' [NEW]' if g in new_groups else ''
                f.write(f"{g}{marker}\n")
        return len(new_groups), len(all_groups)

    try:
        new_count, total_count = log("Processing IOE groups data... ", save_log)
        if new_count > 0:
            print(f"{OK} Saved {new_count} new groups (marked with [NEW]) in '{filename}'.")
        else:
            print(f"[INFO]: No new IOE groups found since last run.")
        print(f"[INFO]: Total IOE groups: {total_count} in '{os.path.abspath(filename)}'.")
    except Exception as e:
        print(f"{E} {e}")


if __name__ == '__main__':
    start_time = time.time()
    print(f"{INFO} Start of IOE groups scraper {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print(f"\n{INFO} Connection to IOE website with groups.")

    url, description = load_url_from_config(category="groups", faculty="ioe", url_type="url_lato")
    from connection import test_connection_with_monitoring 
    test_connection_with_monitoring(url, description)
    if not url:
        print(f"{E} No URL for groups.")
        sys.exit(1)

    try:
        groups = scrape_groups_ioe(url)
        if groups:
            save_to_file(groups)
        else:
            print(f"{W} No IOE groups extracted.")
    except Exception as e:
        print(f"{E} {e}")

    duration = time.time() - start_time
    print(f"{INFO} IOE groups scraper finished {datetime.now().strftime('%Y-%m-%d %H:%M')}   duration: {duration:.2f}s")
