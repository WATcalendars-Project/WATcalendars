"""
WAT Employees Scraper - scrapes employee information from WAT USOS system and saves to JSON format.
"""

import time
import os
import sys
from datetime import datetime

from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.connection import test_connection_with_monitoring
from watcalendars.utils.parsers.employee_parser import detect_total_pages, parse_employees_page, scrape_employees_html
from watcalendars.utils.writers.employees_writer import save_employees_to_json


def scrape_employees_sync(base_url: str, total_pages: int) -> list[tuple[str, str]]:
    """Synchronous scraping of all employee pages."""
    all_employees = []

    
    for page_num in range(1, total_pages + 1):
        page_url = f"{base_url}&page={page_num}"

        
        try:
            [].append(f"Scraping page {page_num}..."); print(f"Scraping page {page_num}...")
            html = scrape_employees_html(page_url)
            if html:
                employees = parse_employees_page(html, page_num, total_pages)
                all_employees.extend(employees)
            else:
                [].append(f"{WARNING} Failed to fetch page {page_num}"); print(f"{WARNING} Failed to fetch page {page_num}")
        except Exception as e:
            [].append(f"{ERROR} Error scraping page {page_num}: {e}"); print(f"{ERROR} Error scraping page {page_num}: {e}")
    

    return all_employees


def main():
    """Main function to coordinate employee scraping process."""
    start_time = time.time()
    print(f"\n------[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting WAT employees scraper:------\n")
    
    try:
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "db", "url_for_employees.json")
        url, description = load_url_from_config(config_file, "usos", "url")
        if not url:
            [].append(f"{ERROR} Failed to load URL configuration"); print(f"{ERROR} Failed to load URL configuration")
            return
    except Exception as e:
        [].append(f"{ERROR} Error loading URL config: {e}"); print(f"{ERROR} Error loading URL config: {e}")
        return
    
    test_connection_with_monitoring(url, description)
    print("")
    
    def detect_pages():
        return detect_total_pages(url)
    
    total_pages = (print(f"{INFO} Detecting total number of pages..."), detect_pages())[1]
    
    if 0 < total_pages < 54:
        print(f"Summary: Total pages detected: {total_pages}")
        print(f"{WARNING} Number of pages is lower than expected")
    elif total_pages >= 54:
        print(f"{OK} Summary: Total pages detected: {total_pages}")
    else:
        print(f"{ERROR} Failed to detect pages")
        return
    print("")
    
    print(f"{INFO} Scraping from URL: {url}&page=1...{total_pages}")
    
    def scrape_all():
        return scrape_employees_sync(url, total_pages)
    
    try:
        all_employees = scrape_all()
        print("")
        if all_employees:
            save_employees_to_json(all_employees)
        else:
            print(f"{ERROR} No data to save.")
            
    except Exception as e:
        print(f"{ERROR} Scraping failed: {e}")
    
    duration = time.time() - start_time
    print("")
    print(f"{INFO} WAT employees scraper finished | duration: {duration:.2f}s")
    print("")

if __name__ == "__main__":
    main()
