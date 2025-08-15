import asyncio
import sys
import re
import os
import time
from watcalendars import DB_DIR
from watcalendars.utils.logutils import OK, WARNING as W, ERROR as E, INFO, log_entry, log
from watcalendars.utils.url_loader import load_url_from_config
from watcalendars.utils.connection import test_connection_with_monitoring
from playwright.async_api import async_playwright 
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime


def detect_total_pages():
    print(f"Finding max number of pages to scrape:")
    logs = []

    def log_detect_pages():

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                log_entry("Browser launched (chromium, headless=True)", logs)
                page = browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

                log_entry(f"Navigating to URL: {url}", logs)
                t0 = time.monotonic()
                resp = page.goto(url, timeout=30000)
                elapsed_ms = int((time.monotonic() - t0) * 1000)

                status = resp.status if resp else None
                ok = getattr(resp, "ok", None) if resp else None
                log_entry(f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}", logs)

                page.wait_for_selector("div.uwb-page-switcher-panel", timeout=5000)
                page.wait_for_load_state("networkidle")

                html = page.content()
                log_entry(f"Getting page content... Done.", logs)

                soup = BeautifulSoup(html, 'html.parser')
                log_entry(f"Parsing HTML content... Done.", logs)

                pagination = soup.find("div", class_="uwb-page-switcher-panel")
                log_entry(f"Pagination element found: \"{pagination}\".", logs)

            except Exception:
                page.wait_for_load_state("networkidle")
                log_entry(f"{E} Failed to load page or find pagination element.", logs)
                print(f"\r{' ' * 80}\r{log_entry}")

            finally:
                browser.close()
                log_entry(f"Closing browser... Done.", logs)

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

    if 0 < total_pages < 54:
        print(f"Summary: Total pages detected: {total_pages}")
        print(f"{W} Number of pages is lower than expected")
    elif total_pages >= 54:
        print(f"{OK} Summary: Total pages detected: {total_pages}")

    return total_pages


async def scrape_page(page, url, page_num):
    max_retries = 3
    retry_count = 0
    page_employees = []
    logs = []

    while retry_count < max_retries:

        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            html = await page.content()

            if "pracownicyJednostki" not in html:
                raise Exception(f"{W} Page {page_num} may not have loaded correctly. Content check failed")
            
            soup = BeautifulSoup(html, "html.parser")
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
            
            if retry_count > 0:
                time.sleep(0.3)
                log_entry(f"{OK} Finished scraping page ({page_num}/{total_pages}) at {retry_count} retries.  Found {len(page_employees)} employees.", logs)
            
            else:
                time.sleep(0.3)
                log_entry(f"{OK} Finished scraping page ({page_num}/{total_pages}) found {len(page_employees)} employees.", logs)

            break

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
    semaphore = asyncio.Semaphore(8)

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

        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        tasks = []

        for page_num in range(1, total_pages + 1):
            page_url = url + "&page=" + str(page_num)
            task = scrape_page_with_semaphore(semaphore, context, page_url, page_num)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        for result in results:
            employees.extend(result)

        await browser.close()

    return employees


def save_to_file(employees):
    filename = os.path.join(DB_DIR, "employees.txt")

    if not os.path.exists(filename):
        print(f"Created a new db file for WAT employees: '{os.path.abspath(filename)}'")
    else:
        print(f"Using existing db file for WAT employees: '{os.path.abspath(filename)}'")

    def save_log():
        logs = []
        existing_employees = set()

        if os.path.exists(filename):

            try:
                with open(filename, "r", encoding="utf-8") as f:

                    for line in f:

                        if line.strip() and not line.startswith("#"):
                            parts = line.strip().split("\t")

                            if len(parts) >= 2:
                                degree = parts[0].strip()
                                full_name = parts[1].replace(" [NEW]", "").strip()
                                existing_employees.add((degree, full_name))

                    log_entry(f"Reading existing employees... Done.", logs)
                    log_entry(f"Skipping empty lines and comments... Done.", logs)

            except Exception:
                pass
        
        normalized_employees = set()

        for degree, full_name in employees:
            normalized_degree = degree.strip()
            normalized_name = full_name.strip()
            normalized_employees.add((normalized_degree, normalized_name))
        log_entry(f"Normalizing employee data and finding new employees... Done.", logs)

        current_employees = normalized_employees
        log_entry(f"Current employees to save: {len(current_employees)}", logs)
        
        new_employees = current_employees - existing_employees
        log_entry(f"Existing employees loaded: {len(existing_employees)}", logs)
        
        all_employees = existing_employees | current_employees
        log_entry(f"New employees detected: {len(new_employees)}", logs)

        with open(filename, "w", encoding="utf-8") as f:
            log_entry(f"Opening db file '{os.path.abspath(filename)}'... Done.", logs)
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

            log_entry(f"Writing header and metadata... Done.", logs)

        return len(new_employees), len(all_employees)
    
    try:
        new_count, total_count = log(f"Saving employees...", save_log)

        if new_count > 0:
            print(f"{OK} Summary: Saved {new_count} employees (marked with [NEW]) in '{os.path.abspath(filename)}'.")
        
        else:
            print(f"{OK} Summary: No new employees found since last run.")

        print(f"[INFO]: Total employees in '{os.path.abspath(filename)}' ({total_count})")

    except Exception as e:
        print(f"{E} {e}")

        
if __name__ == "__main__":

    start_time = time.time()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting WAT employees scraper:")

    url, description = load_url_from_config(key="usos", url_type="url") 
    test_connection_with_monitoring(url, description)

    total_pages = detect_total_pages()

    def scrape_all_pages():
        return asyncio.run(scrape_employees_playwright_async(total_pages, url))

    print(f"Async scraping from URL: {url}&page=1...{total_pages}")

    try:
        all_employees = log(f"Async scraping pages...", scrape_all_pages)

        if all_employees:
            save_to_file(all_employees)

        else:
            print(f"{E} No data to save.")

    except Exception as e:
        print(f"{E} {e}")

    duration = time.time() - start_time
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] WAT employees scraper finished  |  duration: {duration:.2f}s")