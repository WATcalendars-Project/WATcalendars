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

# --- SIMPLE APPROACH: first <td valign="TOP"> if exists, else all .htm/.html hrefs (fallback) ---

def scrape_groups_wml(url):
    print(f"\n{INFO} Scrape WML groups (simple column mode).")
    logs = []

    def extract_tokens(container):
        groups = set()
        for a in container.find_all('a', href=True):
            href = a['href']
            if not href.lower().endswith(('.htm', '.html')):
                continue
            base = href.rsplit('/', 1)[-1].split('?')[0].split('#')[0]
            base_no_ext = re.sub(r'\.(?:htm|html)$', '', base, flags=re.IGNORECASE).strip()
            if not base_no_ext:
                continue
            token = '_'.join(base_no_ext.split())
            groups.add(token)
        return groups

    def log_scrape():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'
            ])
            page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")
            page.goto(url, timeout=30000)
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, 'html.parser')

        first_td = None
        for td in soup.find_all('td'):
            if td.get('valign', '').upper() == 'TOP':
                first_td = td
                break
        if first_td:
            groups = extract_tokens(first_td)
            log_entry(f"Collected {len(groups)} groups from the first column.", logs)
        else:
            groups = extract_tokens(soup)
            log_entry(f"No <td valign=TOP> – fallback collected {len(groups)} groups from whole page.", logs)
        return sorted(groups)

    groups = log("Scraping WML groups list... ", log_scrape)
    print(f"{OK} Scraped {len(groups)} WML groups (simple).")
    return groups


def save_to_file(groups):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(script_dir, "..", "..", "..", "db", "groups")
    os.makedirs(db_dir, exist_ok=True)
    filename = os.path.join(db_dir, "wml.txt")

    def parse_existing():
        existing = set()
        if not os.path.exists(filename):
            return existing
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    existing.add(re.sub(r"\s+\[NEW\]$", "", line))
        except Exception:
            pass
        return existing

    def save_log():
        existing = parse_existing()
        current = set(groups)
        new_groups = current - existing
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('# WML Groups list (simple extraction)\n')
            f.write(f"# Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total number of groups: {len(current)}\n")
            f.write(f"# New groups in this run: {len(new_groups)}\n")
            f.write('# Format: one token (href basename) per line; new ones marked with [NEW]\n\n')
            for g in sorted(current):
                marker = ' [NEW]' if g in new_groups else ''
                f.write(f"{g}{marker}\n")
        return len(new_groups), len(current)

    try:
        new_count, total_count = log("Saving WML groups file... ", save_log)
        if new_count:
            print(f"{OK} {new_count} new WML groups (marked with [NEW]).")
        print(f"[INFO]: Total WML groups: {total_count} in '{os.path.abspath(filename)}'.")
    except Exception as e:
        print(f"{E} {e}")


if __name__ == '__main__':
    start_time = time.time()
    print(f"{INFO} Start of WML groups scraper {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print(f"\n{INFO} Connection to WML website with groups.")

    url, description = load_url_from_config(category="groups", faculty="wml", url_type="url")
    from connection import test_connection_with_monitoring
    test_connection_with_monitoring(url, description)
    if not url:
        print(f"{E} No URL for groups.")
        sys.exit(1)

    try:
        groups = scrape_groups_wml(url)
        if groups:
            save_to_file(groups)
        else:
            print(f"{W} No WML groups extracted.")
    except Exception as e:
        print(f"{E} {e}")

    duration = time.time() - start_time
    print(f"{INFO} WML groups scraper finished {datetime.now().strftime('%Y-%m-%d %H:%M')}   duration: {duration:.2f}s")
