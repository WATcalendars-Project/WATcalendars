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
                log_entry(f"Navigating to URL: {url}", logs)
                t0 = time.monotonic()
                resp = page.goto(url, timeout=timeout)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                status = resp.status if resp else None
                ok = getattr(resp, "ok", None) if resp else None
                log_entry(
                    f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}",
                    logs,
                )
                
                # --- KLUCZOWA ZMIANA ---
                # Jeśli to odpowiedź z serwera (np. plik XML/JSON), pobieramy czysty tekst z sieci.
                # page.content() używamy tylko jako ostateczności dla czystego HTML.
                if resp:
                    try:
                        html = resp.text()
                    except:
                        html = page.content()
                else:
                    html = page.content()
                # -----------------------

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

    # Wypakowujemy wyniki z dekoratora
    html, logs = log("Scraping...", scrape_html_with_logs)
    
    # POPRAWKA: Usunięto nawiasy klamrowe, które tworzyły zbiór (set)
    html_length = len(html) if html else 0
    if html_length > 0:
        print(f"{SUCCESS} Scraped {url} ({html_length} bytes)")
    else:
        print(f"{ERROR} Failed to scrape {url}")
        
    return html, logs
