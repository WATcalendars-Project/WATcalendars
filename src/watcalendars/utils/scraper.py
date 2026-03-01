import os
import time
import asyncio
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright, TimeoutError as AsyncPlaywrightTimeoutError


def scrape_html(url, user_agent=None, timeout=25000, logs=None):
    """
    Synchronous fallback scraper (chromium headless).
    """
    logs = logs if logs is not None else []

    def scrape_html_with_logs():
        html = None
        with sync_playwright() as p:
            browser = p.firefox.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            try:
                logs.append("Browser launched (chromium, headless=True)."); print("Browser launched (chromium, headless=True).")
                page = browser.new_page(
                    user_agent=user_agent
                    or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                logs.append(f"Navigating to URL: {url}"); print(f"Navigating to URL: {url}")
                t0 = time.monotonic()
                resp = page.goto(url, timeout=timeout)
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                status = resp.status if resp else None
                ok = getattr(resp, "ok", None) if resp else None
                logs.append(f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}"); print(f"Navigation done: status={status}, ok={ok}, elapsed_ms={elapsed_ms}")
                
                # --- KLUCZOWA ZMIANA: Obsługa surowych bajtów (odpowiedź XML/JSON z polskim kodowaniem) ---
                if resp:
                    try:
                        # Próbujemy odczytać bezpośrednio bajty i wymuszamy dekodowanie windows-1250 (używane na WAT)
                        html = resp.body().decode('windows-1250', errors='replace')
                    except Exception as e:
                        logs.append(f"[WARNING] Failed to decode body (falling back to content): {e}"); print(f"[WARNING] Failed to decode body (falling back to content): {e}")
                        html = page.content()
                else:
                    html = page.content()
                # -----------------------

                logs.append("Getting page content."); print("Getting page content.")
            except PlaywrightTimeoutError as e:
                logs.append(f"[WARNING] Timeout navigating to {url}: {e}"); print(f"[WARNING] Timeout navigating to {url}: {e}")
                raise
            except Exception as e:
                logs.append(f"[ERROR] Unhandled error while scraping {url}: {e}"); print(f"[ERROR] Unhandled error while scraping {url}: {e}")
                raise
            finally:
                browser.close()
                logs.append("Closing browser."); print("Closing browser.")
        return html, logs

    # Wypakowujemy wyniki z dekoratora logów
    html, logs = (print("Scraping..."), scrape_html_with_logs())[1]
    
    # Poprawka: Obliczanie długości
    html_length = len(html) if html else 0
    if html_length > 0:
        print(f"[SUCCESS] Scraped {url} ({html_length} bytes)")
        
        # Opcjonalny DEBUG, jeśli wciąż widać dziwnie mały rozmiar pliku (<1000 bajtów).
        # Odkomentuj 3 linijki poniżej, jeśli scraper nie znajdzie grup, by zobaczyć co naprawdę pobrał.
        # if html_length < 2000:
        #     print("\n--- DEBUG POBRANEGO PLIKU ---")
        #     print(html[:500])
        #     print("-----------------------------\n")
    else:
        print(f"[ERROR] Failed to scrape {url}")
        
    return html, logs


def fetch_group_html(browser, idx, total, group, url, faculty_prefix="", logs=None, timeout=25000, wait_timeout=5000):
    """
    Sync scraper for a single group with retries.
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
            
            logs.append(f"[SUCCESS] Scraping {group} completed."); print(f"[SUCCESS] Scraping {group} completed.")
            
             
            break
            
        except PlaywrightTimeoutError as e:
            retry_count += 1
            logs.append(f"[WARNING] Timeout for {group} (retry {retry_count}/{max_retries})"); print(f"[WARNING] Timeout for {group} (retry {retry_count}/{max_retries})")
            if retry_count < max_retries:
                time.sleep(2)  
        except Exception as e:
            retry_count += 1
            logs.append(f"[WARNING] Error for {group} (retry {retry_count}/{max_retries}): {str(e)[:50]}..."); print(f"[WARNING] Error for {group} (retry {retry_count}/{max_retries}): {str(e)[:50]}...")
            if retry_count < max_retries:
                time.sleep(1)  
            
        finally:
            try:
                page.close()
            except:
                pass  
                
        if retry_count >= max_retries:
            logs.append(f"[ERROR] Failed to scrape group {group} after {max_retries} attempts"); print(f"[ERROR] Failed to scrape group {group} after {max_retries} attempts")
            
                
    return html


