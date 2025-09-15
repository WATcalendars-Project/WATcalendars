"""
Employee Parser - Parsing employees from WAT USOS HTML pages
"""

import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from watcalendars.utils.logutils import OK, WARNING as W, ERROR as E, log_entry


def scrape_employees_html(url: str, timeout: int = 30000) -> str:
    """
    Scrape employee HTML with proper waiting for dynamic content.
    
    Args:
        url: URL to scrape
        timeout: Timeout in milliseconds
        
    Returns:
        str: HTML content or empty string if failed
    """
    logs = []
    html = ""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            t0 = time.monotonic()
            resp = page.goto(url, timeout=timeout)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            status = resp.status if resp else None
            ok = getattr(resp, "ok", None) if resp else None
            log_entry(f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}", logs)
            
            try:
                page.wait_for_selector("td.uwb-staffuser-panel", timeout=10000)
            except PlaywrightTimeoutError:
                log_entry(f"{W} Employee panels not found within timeout", logs)
                page.wait_for_load_state("networkidle", timeout=5000)
            html = page.content()
            
        except Exception as e:
            log_entry(f"{E} Failed to scrape page: {e}", logs)
        finally:
            browser.close()
    
    return html


def detect_total_pages(url: str) -> int:
    """
    Detect the total number of pages by parsing the pagination element.
    
    Args:
        url: Base URL to check for pagination
        
    Returns:
        int: Total number of pages, or 1 if detection fails
    """
    logs = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            log_entry("Browser launched (chromium, headless=True)", logs)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            log_entry(f"Navigating to URL: {url}", logs)
            t0 = time.monotonic()
            resp = page.goto(url, timeout=30000)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            status = resp.status if resp else None
            ok = getattr(resp, "ok", None) if resp else None
            log_entry(f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}", logs)
            
            try:
                page.wait_for_selector("div.uwb-page-switcher-panel", timeout=5000)
                page.wait_for_load_state("networkidle")
            except Exception:
                log_entry(f"{W} Pagination element not found within timeout", logs)
            
            html = page.content()
            log_entry(f"Getting page content.", logs)
            
            soup = BeautifulSoup(html, 'html.parser')
            log_entry(f"Parsing HTML content.", logs)
            
            pagination = soup.find("div", class_="uwb-page-switcher-panel")
            
            if pagination:
                td = pagination.find("td")
                if td:
                    text = td.get_text(strip=True)
                    log_entry(f"Pagination text found: \"{text}\".", logs)
                    match = re.search(r'/\s*(\d+)', text)
                    if match:
                        total_pages = int(match.group(1))
                        log_entry(f"Total pages detected: {total_pages}", logs)
                        return total_pages
                    else:
                        log_entry(f"{E} No page number found in pagination text.", logs)
                        return 1
                else:
                    log_entry(f"{E} No td element found in pagination.", logs)
                    return 1
            else:
                log_entry(f"{E} No pagination nav found. Assuming only 1 page.", logs)
                return 1
                
        except Exception as e:
            log_entry(f"{E} Failed to load page or find pagination element: {e}", logs)
            return 1
        finally:
            browser.close()
            log_entry(f"Closing browser.", logs)


def parse_employees_page(html: str, page_num: int, total_pages: int) -> list[tuple[str, str]]:
    """
    Parse employee information from a single HTML page.
    
    Args:
        html: HTML content of the page
        page_num: Current page number (for logging)
        total_pages: Total number of pages (for logging)
        
    Returns:
        list: List of tuples containing (degree, full_name)
    """
    employees = []
    
    if not html:
        print(f"\n{E} Empty HTML for page {page_num}")
        return employees
    
    if "pracownicyJednostki" not in html:
        print(f"\n{W} Page {page_num} may not have loaded correctly. Content check failed")
        return employees
    
    try:
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
                    employees.append((degree_text, full_name))
                    
        log_entry(f"{OK} Found {len(employees)} employees", [])
        
    except Exception as e:
        print(f"\n{E} Error parsing page {page_num}: {e}")
    
    return employees
