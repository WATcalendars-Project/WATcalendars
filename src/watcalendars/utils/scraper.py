import os
import time
import asyncio
from watcalendars.utils.logutils import (
    log_entry,
    log,
    SUCCESS,
    WARNING,
    ERROR,
    OK,
    start_spinner,
    spinner_progress,
    log_parsing,
)
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright, TimeoutError as AsyncPlaywrightTimeoutError
from watcalendars.utils.writers.screenshot_writer import save_screenshot_async, get_target_dir

# --- DODANY IMPORT WTYCZKI STEALTH ---
from playwright_stealth import stealth_sync
# -------------------------------------

def scrape_html(url, user_agent=None, timeout=25000, logs=None):
    """
    Synchronous fallback scraper (chromium headless).
    """
    logs = logs if logs is not None else []

    def scrape_html_with_logs():
        html = None
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            try:
                log_entry("Browser launched (chromium, headless=True).", logs)
                page = browser.new_page(
                    user_agent=user_agent
                    or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                
                # --- AKTYWACJA TRYBU STEALTH DLA TEJ ZAKŁADKI ---
                stealth_sync(page)
                # ------------------------------------------------
                
                log_entry(f"Navigating to URL: {url}", logs)
                t0 = time.monotonic()
                
                # Czekamy na załadowanie wszystkich skryptów przeciw botom
                resp = page.goto(url, timeout=timeout, wait_until="networkidle")
                
                # Dajemy Incapsuli czas na ustawienie ciastek i przeładowanie ukrytej ramki/strony
                page.wait_for_timeout(3500) 

                elapsed_ms = int((time.monotonic() - t0) * 1000)
                status = resp.status if resp else None
                ok = getattr(resp, "ok", None) if resp else None
                log_entry(
                    f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}",
                    logs,
                )
                
                if resp:
                    try:
                        html = resp.body().decode('windows-1250', errors='replace')
                    except Exception as e:
                        log_entry(f"{WARNING} Failed to decode body (falling back to content): {e}", logs)
                        html = page.content()
                else:
                    html = page.content()

                log_entry("Getting page content.", logs)
            except PlaywrightTimeoutError as e:
                log_entry(f"{WARNING} Timeout navigating to {url}: {e}", logs)
                raise
            except Exception as e:
                log_entry(f"{ERROR} Unhandled error while scraping {url}: {e}", logs)
                raise
            finally:
                browser.close()
                log_entry("Closing browser.", logs)
        return html, logs

    # Wypakowujemy wyniki z dekoratora logów
    html, logs = log("Scraping...", scrape_html_with_logs)
    
    # Poprawka: Obliczanie długości
    html_length = len(html) if html else 0
    if html_length > 0:
        print(f"{SUCCESS} Scraped {url} ({html_length} bytes)")
    else:
        print(f"{ERROR} Failed to scrape {url}")
        
    return html, logs


def fetch_group_html(browser, idx, total, group, url, faculty_prefix="", logs=None, timeout=25000, wait_timeout=5000):
    """
    Sync scraper for a single group with retries and screenshot saving (success/fail).
    Optimized for speed with configurable timeouts.

    Args:
        timeout: Page load timeout (default: 25s)
        wait_timeout: Timeout for waiting on elements (default: 5s)
    """
    max_retries = 3  
    retry_count = 0
    html = None
    logs = logs or []

    while retry_count < max_retries:
        page = browser.new_page()
        
        # --- AKTYWACJA TRYBU STEALTH TAKŻE DLA POBIERANIA KONKRETNEJ GRUPY ---
        stealth_sync(page)
        # ---------------------------------------------------------------------
        
        try:
            page.set_default_timeout(timeout)
            
            if "wcy.wat.edu.pl" in url:
                response = page.goto(url, wait_until="load", timeout=timeout)
                try:
                    page.wait_for_selector(".rozklad, table, .schedule", timeout=wait_timeout)
                except:
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except:
                        time.sleep(2)  
            else:
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                try:
                    page.wait_for_selector("table, .content, body", timeout=wait_timeout)
                except:
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass
            
            if not response or not response.ok:
                raise Exception(f"HTTP {response.status if response else 'No response'}")
            
            html = page.content()
            if len(html) < 200:  
                raise Exception("Page content too short")
            
            log_entry(f"{SUCCESS} Scraping {group} completed.", logs)
            
            # (Uwaga: upewnij się, że masz zdefiniowaną funkcję save_screenshot, w importach widać save_screenshot_async)
            # save_screenshot(page, group, faculty_prefix) 
            break
            
        except PlaywrightTimeoutError as e:
            retry_count += 1
            log_entry(f"{WARNING} Timeout for {group} (retry {retry_count}/{max_retries})", logs)
            if retry_count < max_retries:
                time.sleep(2)  
        except Exception as e:
            retry_count += 1
            log_entry(f"{WARNING} Error for {group} (retry {retry_count}/{max_retries}): {str(e)[:50]}...", logs)
            if retry_count < max_retries:
                time.sleep(1)  
            
        finally:
            try:
                page.close()
            except:
                pass  
                
        if retry_count >= max_retries:
            log_entry(f"{ERROR} Failed to scrape group {group} after {max_retries} attempts", logs)
            try:
                if 'page' in locals() and page:
                    # save_screenshot(page, group, faculty_prefix)
                    pass
            except Exception:
                print(f"{ERROR} Failed to save screenshot for {group}")
                
    return html
