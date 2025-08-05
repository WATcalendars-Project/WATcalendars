#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import re
import os
import time
from logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log
from url_loader import load_url_from_config
from playwright.async_api import async_playwright 
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime

# synchronous detection of total number of pages for employees
def detect_total_pages():
    print(f"\n{INFO} Find max number of pages to scrape.")

    # function for logs from logutils
    def log_detect_pages():
        # table to store logs
        logs = []
        # Function to log messages
        with sync_playwright() as p:
            # Launch the browser and navigate to the URL
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page.goto(url, timeout=30000)
            log_entry(f"Launched browser to find max number of pages.", logs)
            log_entry(f"URL: {url}", logs)
            # Wait for the page to load and check for pagination
            try:
                page.wait_for_selector("div.uwb-page-switcher-panel", timeout=5000)
                page.wait_for_load_state("networkidle")
                log_entry(f"Page loaded successfully.", logs)
            except Exception:
                page.wait_for_load_state("networkidle")
                log_entry(f"{E} Failed to load page or find pagination element.", logs)
                print(f"\r{' ' * 80}\r{log_entry}")
            # Get the pagination element
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            pagination = soup.find("div", class_="uwb-page-switcher-panel")
            log_entry(f"Pagination element found: \"{pagination}\".", logs)
            browser.close()
            log_entry(f"Browser closed.", logs)

        # Check if pagination exists and extract the total number of pages
        if pagination:
            td = pagination.find("td")
            log_entry(f"Pagination text found: \"{td.get_text(strip=True)}\".", logs)
            if td:
                text = td.get_text(strip=True)
                match = re.search(r'/\s*(\d+)', text)
                if match:
                    return int(match.group(1))
                else:
                    log_entry(f"{E} No page number found in pagination text.", logs)
                    return 1
            else:
                log_entry(f"{E} No page number found in pagination text.", logs)
                return 1
        else:
            log_entry(f"{E} No pagination nav found. Assuming only 1 page.", logs)
            return 1

    total_pages = log(f"Detecting total number of pages...", log_detect_pages)

    # Print the total number of pages detected
    if 0 < total_pages < 54:
        print(f"Summary: Total pages detected: {total_pages}")
        print(f"{W} Number of pages is lower than expected")
    elif total_pages >= 54:
        print(f"Summary: Total pages detected: {total_pages}")
        print(f"{OK} Pages detection completed.")

    return total_pages



# Asynchronous scraping of employee data from WAT
async def scrape_page(page, url, page_num):
    # Define a list to store employees from the current page and a maximum number of retries
    max_retries = 3
    retry_count = 0
    page_employees = []
    logs = []
    # Try to scrape the page with retries
    while retry_count < max_retries:
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            html = await page.content()

            # Check if the "pracownicyJednostki" are present in the HTML content
            if "pracownicyJednostki" not in html:
                raise Exception(f"{W} Page {page_num} may not have loaded correctly. Content check failed")
            
            # Parse the HTML content with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            # Find all employee panels
            panels = soup.find_all("td", class_="uwb-staffuser-panel")

            for panel in panels:
                name_tag = panel.find("b")
                degree_link = panel.find("a", class_="no-badge uwb-photo-panel-title")
                if name_tag and degree_link:
                    full_name = name_tag.text.strip()
                    degree_text = degree_link.text.replace(full_name, "").strip()
                    degree_text = ' '.join(degree_text.split())
                    if full_name and degree_text:
                        page_employees.append((degree_text, full_name))
            
            # Print the status of the scraping
            if retry_count > 0:
                time.sleep(0.3)
                log_entry(f"Finished scraping page ({page_num}/{total_pages}) at {retry_count} retries", logs)
            else:
                time.sleep(0.3)
                log_entry(f"Finished scraping page ({page_num}/{total_pages})  found {len(page_employees)} employees.", logs)
            break

        # If the page fails to load or scrape, retry
        except Exception as e:
            retry_count += 1
            time.sleep(0.3)
            log_entry(f"{W} Retry {retry_count}/{max_retries} for page ({page_num}/{total_pages})...", logs)
            if retry_count < max_retries:
                await asyncio.sleep(3)
                continue
            else:
                time.sleep(0.3)
                log_entry(f"{E} Failed to scrape page ({page_num}/{total_pages}) after {max_retries} attempts", logs)
                break

    return page_employees



async def scrape_page_with_semaphore(semaphore, context, url, page_num):
    async with semaphore:
        page = await context.new_page()
        result = await scrape_page(page, url, page_num)
        await page.close()
        return result



async def scrape_employees_playwright_async(total_pages, url):
    employees = []
    
    # Create a semaphore to limit concurrent page loads
    semaphore = asyncio.Semaphore(11)

    # Use Playwright to launch the browser and scrape pages concurrently
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080'
            ]
        )
        # Create a new browser context with a user agent
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        # Create a list of tasks to scrape for each page
        tasks = []
        for page_num in range(1, total_pages + 1):
            page_url = url + "&page=" + str(page_num)
            task = scrape_page_with_semaphore(semaphore, context, page_url, page_num)
            tasks.append(task)

        # Gather results from all tasks and extend the employees list
        results = await asyncio.gather(*tasks)
        for result in results:
            employees.extend(result)

        await browser.close()

    return employees


def save_to_file(employees):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(script_dir, "..", "..", "db")
    filename = os.path.join(db_dir, "employees.txt")
    if not os.path.exists(filename):
        print(f"Created a new db file for WAT employees: '{os.path.abspath(filename)}'")
    else:
        print(f"Using existing db file for WAT employees: '{os.path.abspath(filename)}'")

    # Save the employees to a file
    def save_log():
        logs = []
        # Check if the file exists and read existing employees
        existing_employees = set()
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    log_entry(f"Reading existing employees.", logs)
                    log_entry(f"Skipping empty lines and comments.", logs)
                    log_entry(f"Extracting employee data.", logs)
                    for line in f:
                        # Skip empty lines and comments
                        if line.strip() and not line.startswith("#"):
                            parts = line.strip().split("\t")
                            # Ensure there are at least two parts (degree and full name)
                            if len(parts) >= 2:
                                # Extract degree and full name, removing any trailing markers like [NEW]
                                degree = parts[0].strip()
                                full_name = parts[1].replace(" [NEW]", "").strip()
                                existing_employees.add((degree, full_name))
            except Exception:
                pass
        
        # Normalize the employees list and find new employees
        # Use a set to ensure uniqueness and normalize the data
        log_entry(f"Normalizing employee data and finding new employees.", logs)
        normalized_employees = set()
        for degree, full_name in employees:
            normalized_degree = degree.strip()
            normalized_name = full_name.strip()
            normalized_employees.add((normalized_degree, normalized_name))
        current_employees = normalized_employees
        new_employees = current_employees - existing_employees
        all_employees = existing_employees | current_employees

        with open(filename, "w", encoding="utf-8") as f:
            log_entry(f"Open db file '{os.path.abspath(filename)}'.", logs)
            f.write("# Employee list of WAT\n")
            f.write(f"# Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total number of employees: {len(all_employees)}\n")
            if new_employees:
                f.write(f"# New employees found in this run: {len(new_employees)}\n")
                log_entry(f"Found {len(new_employees)} new employees.", logs)
            f.write("\n")
            for degree, full_name in sorted(all_employees):
                marker = " [NEW]" if (degree, full_name) in new_employees else ""
                f.write(f"{degree}\t{full_name}{marker}\n")
        return len(new_employees), len(all_employees)
    
    try:
        new_count, total_count = log(f"Saving employees...", save_log)
        if new_count > 0:
            print(f"{OK} Summary: Saved {new_count} employees (marked with [NEW]) in '{os.path.abspath(filename)}'.")
        else:
            print(f"Summary: No new employees found since last run.")
        print(f"Total employees in '{os.path.abspath(filename)}' ({total_count})")
    except Exception as e:
        print(f"{E} {e}")


        
if __name__ == "__main__":
    start_time = time.time()
    print(f"{INFO} Start of WAT employees scraper {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    # Check connection to USOS WAT server with employee data
    print(f"\n{INFO} Connection to USOS WAT server with employee data.")

    url, description = load_url_from_config(category="usos", faculty="", url_type="")

    from connection import test_connection_with_monitoring 
    test_connection_with_monitoring(url, description)

    total_pages = detect_total_pages()

    def scrape_all_pages():
        return asyncio.run(scrape_employees_playwright_async(total_pages, url))

    print(f"\n{INFO} Async scraping pages from URL: {url}&page=1...{total_pages}")
    try:
        all_employees = log(f"Scraping pages...", scrape_all_pages)
        if all_employees:
            save_to_file(all_employees)
        else:
            print(f"{W} No data to save.")
    except Exception as e:
        print(f"{E} {e}")
    duration = time.time() - start_time
    print(f"{INFO} WAT employees scraper finished {datetime.now().strftime('%Y-%m-%d %H:%M')}   duration: {duration:.2f}s")