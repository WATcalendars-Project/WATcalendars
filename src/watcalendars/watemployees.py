"""
WAT Employees Scraper - scrapes employee information from WAT USOS system and saves to JSON format.
"""

import time
import os
import sys
from datetime import datetime

from watcalendars.utils.logutils import OK, WARNING as W, ERROR as E, log, spinner_progress, log_entry
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.parsers.employee_parser import detect_total_pages, parse_employees_page, scrape_employees_html
from watcalendars.utils.writers.employees_writer import save_employees_to_json


def scrape_employees_sync(base_url: str, total_pages: int) -> list[tuple[str, str]]:
    """Synchronous scraping of all employee pages."""
    all_employees = []
    spinner = spinner_progress("Scraping employees", total_pages)
    
    for page_num in range(1, total_pages + 1):
        page_url = f"{base_url}&page={page_num}"
        spinner.update(page_num)
        
        try:
            log_entry(f"Scraping page {page_num}:", [])
            html = scrape_employees_html(page_url)
            if html:
                employees = parse_employees_page(html, page_num, total_pages)
                all_employees.extend(employees)
            else:
                log_entry(f"{W} Failed to fetch page {page_num}", [])
        except Exception as e:
            log_entry(f"{E} Error scraping page {page_num}: {e}", [])
    
    spinner.finish()
    return all_employees


def main():
    """Main function to coordinate employee scraping process."""
    start_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting WAT employees scraper:")
    print("")
    
    try:
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "db", "url_for_employees.json")
        url, description = load_url_from_config(config_file, "usos", "url")
        if not url:
            log_entry(f"{E} Failed to load URL configuration", [])
            return
    except Exception as e:
        log_entry(f"{E} Error loading URL config: {e}", [])
        return
    
    test_connection_with_monitoring(url, description)
    print("")
    
    def detect_pages():
        return detect_total_pages(url)
    
    total_pages = log("Detecting total number of pages...", detect_pages)
    
    if 0 < total_pages < 54:
        print(f"Summary: Total pages detected: {total_pages}")
        print(f"{W} Number of pages is lower than expected")
    elif total_pages >= 54:
        print(f"{OK} Summary: Total pages detected: {total_pages}")
    else:
        print(f"{E} Failed to detect pages")
        return
    print("")
    
    print(f"Synchronous scraping from URL: {url}&page=1...{total_pages}")
    
    def scrape_all():
        return scrape_employees_sync(url, total_pages)
    
    try:
        all_employees = scrape_all()
        print("")
        if all_employees:
            save_employees_to_json(all_employees)
        else:
            print(f"{E} No data to save.")
            
    except Exception as e:
        print(f"{E} Scraping failed: {e}")
    print("")
    
    duration = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WAT employees scraper finished | duration: {duration:.2f}s")


if __name__ == "__main__":
    main()
