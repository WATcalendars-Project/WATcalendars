#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log
from url_loader import load_url_from_config 
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime


def amount_of_groups_detection(url):
    print(f"\n{INFO} Find max number of groups to scrape.")

    logs =[]

    def log_groups_detection():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")
            page.goto(url, timeout=20000)
            log_entry(f"Launched browser to find max number of groups.", logs)
            log_entry(f"URL: {url}", logs)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            browser.close()
        # Extracting group options from the HTML
        # The options are expected to be in a <select> element, typically with a class or id.
        groups = [option.text.strip() for option in soup.find_all("option") if option.text.strip()]
        groups = [group for group in groups if "- Wybierz grupę -" not in group]
        groups = [group.rstrip(".") for group in groups]
        return len(groups)
    
    total_groups = log("Detecting total number of groups... ", log_groups_detection)
    print(f"{OK} Total groups detected: {total_groups}")
    return total_groups


def scrape_groups_playwright(url):
    print(f"\n{INFO} Scrape groups names.")
    logs = []
    def log_scrape_groups():
        groups = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36")
            page.goto(url, timeout=20000)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            options = soup.find_all("option")
            log_entry(f"Open page for scraping", logs)
            for option in options:
                group = option.text.strip()
                # This checks if the group is not empty and does not contain the placeholder text
                # placeholder text is "- Wybierz grupę -"
                if group and "- Wybierz grupę -" not in group:
                    # Remove trailing period if present
                    # This is to ensure that the group name is clean
                    # and does not end with a period.
                    group = group.rstrip(".")
                    groups.append(group)
            browser.close()

        return groups

    groups = log("Scraping groups names... ", log_scrape_groups)
    print(f"{OK} Scraped {len(groups)} groups.")
    return groups


def save_to_file(groups):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(script_dir, "..", "..", "..", "db", "groups")
    filename = os.path.join(db_dir, "wcy.txt")
    if not os.path.exists(filename):
        print(f"Created a new db file for WCY groups: '{os.path.abspath(filename)}'")
    else:
        print(f"Using existing db file for WCY groups: '{os.path.abspath(filename)}'")

    def save_log():
        existing_groups = set()
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip() and not line.startswith("#"):
                            group_name = line.strip()
                            group_name = re.sub(r"\s+\[NEW\]$", "", group_name)
                            existing_groups.add(group_name)
            except Exception:
                pass
        normalized_groups = set(g.strip() for g in groups)
        new_groups = normalized_groups - existing_groups
        all_groups = existing_groups | normalized_groups
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# WCY Groups list\n")
            f.write(f"# Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total number of groups: {len(all_groups)}\n")
            if new_groups:
                f.write(f"# New groups found in this run: {len(new_groups)}\n")
            f.write("\n")
            for group in sorted(all_groups):
                marker = " [NEW]" if group in new_groups else ""
                f.write(f"{group}{marker}\n")
        return len(new_groups), len(all_groups)
    try:
        new_count, total_count = log("Processing groups data... ", save_log)
        if new_count > 0:
            print(f"{OK} Saved {new_count} groups (marked with [NEW]) in '{filename}'.")
        else:
            print(f"[INFO]: No new groups found since last run.")
        print(f"[INFO]: Total groups: {total_count} in '{os.path.abspath(filename)}'.")
    except Exception as e:
        print(f"{E} {e}")

if __name__ == "__main__":
    start_time = time.time()
    print(f"{INFO} Start of WCY groups scraper {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print(f"\n{INFO} Connection to WCY website with groups.")

    url, description = load_url_from_config(key="wcy_groups", url_type="url")

    from connection import test_connection_with_monitoring 
    test_connection_with_monitoring(url, description)

    total_groups = amount_of_groups_detection(url)

    groups = scrape_groups_playwright(url)

    try:
        if groups:
            save_to_file(groups)
        else:
            print(f"{W} No data to save.")
    except Exception as e:
        print(f"{E} {e}")
    duration = time.time() - start_time
    print(f"{INFO} WCY groups scraper finished {datetime.now().strftime('%Y-%m-%d %H:%M')}   duration: {duration:.2f}s")