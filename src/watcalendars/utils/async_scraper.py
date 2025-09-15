"""
Universal asynchronous web scraper for all WAT departments
"""
import asyncio
import time
from playwright.async_api import async_playwright
from watcalendars.utils.logutils import OK, WARNING, ERROR, log_entry, start_spinner


class AsyncScraper:
    """Universal async scraper for WAT departments"""
    
    def __init__(self, concurrency: int = 10, timeout: int = 30000, wait_timeout: int = 15000):
        """
        Initialize AsyncScraper
        
        Args:
            concurrency: Max concurrent pages
            timeout: Page load timeout in ms
            wait_timeout: Network idle wait timeout in ms
        """
        self.concurrency = concurrency
        self.timeout = timeout
        self.wait_timeout = wait_timeout
        self.browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--allow-insecure-localhost",
            "--ignore-certificate-errors",
            "--headless"
        ]

    async def fetch_page_html(self, page, idx, total, identifier, url, max_retries: int = 3):
        """
        Fetch HTML content from a single page with retries
        
        Args:
            page: Playwright page instance
            idx: Current index
            total: Total pages count
            identifier: Page identifier (e.g., group name)
            url: URL to fetch
            max_retries: Maximum retry attempts
            
        Returns:
            tuple: (html_content, logs_list)
        """
        retry_count = 0
        html = None
        logs = []
        
        while retry_count < max_retries:
            try:
                await page.goto(url, timeout=self.timeout)
                await page.wait_for_load_state("networkidle", timeout=self.wait_timeout)
                html = await page.content()
                
                if retry_count == 0:
                    log_entry(f"{OK} Scraping {identifier} completed.", logs)
                else:
                    log_entry(f"{OK} Scraping {identifier} completed after {retry_count} retries.", logs)
                break
                
            except Exception as e:
                retry_count += 1
                log_entry(f"{WARNING} Timeout for {identifier} (retry {retry_count}/{max_retries})", logs)
                
                if retry_count < max_retries:
                    await asyncio.sleep(2)
                else:
                    log_entry(f"{ERROR} Failed to scrape {identifier} after {max_retries} attempts: {e}", logs)
        
        return html, logs

    async def scrape_urls(self, url_pairs, progress_label: str = "Scraping", 
                         save_screenshots: bool = False, screenshot_callback=None):
        """
        Scrape multiple URLs asynchronously
        
        Args:
            url_pairs: List of tuples (identifier, url)
            progress_label: Label for progress spinner
            save_screenshots: Whether to save screenshots
            screenshot_callback: Optional callback for saving screenshots
            
        Returns:
            dict: Mapping of identifier -> html_content
        """
        results = {}
        semaphore = asyncio.Semaphore(self.concurrency)
        
        done = 0
        done_lock = asyncio.Lock()
        all_logs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=self.browser_args)
            context = await browser.new_context()

            stop_event, spinner_task = start_spinner(
                f"{progress_label} groups for", 
                len(url_pairs), 
                lambda: done, 
                interval=0.2
            )

            async def worker(idx_pair):
                nonlocal done
                idx, (identifier, url) = idx_pair

                async with semaphore:
                    page = await context.new_page()

                    try:
                        html, logs = await self.fetch_page_html(
                            page, idx + 1, len(url_pairs), identifier, url
                        )
                        results[identifier] = html
                        
                        for log_msg in logs:
                            print(log_msg)
                        
                        if save_screenshots and screenshot_callback and html:
                            try:
                                await screenshot_callback(page, identifier)
                            except Exception as e:
                                print(f"{WARNING} Failed to save screenshot for {identifier}: {e}")

                    finally:
                        await page.close()
                        async with done_lock:
                            done += 1

            try:
                await asyncio.gather(*[worker(item) for item in enumerate(url_pairs)])
            
            finally:
                stop_event.set()
                await spinner_task
                await browser.close()

        return results

    async def scrape_with_custom_logic(self, url_pairs, custom_fetch_func, progress_label: str = "Scraping"):
        """
        Scrape URLs with custom fetch logic
        
        Args:
            url_pairs: List of tuples (identifier, url)
            custom_fetch_func: Custom async function for fetching (page, identifier, url) -> result
            progress_label: Label for progress spinner
            
        Returns:
            dict: Mapping of identifier -> result
        """
        results = {}
        semaphore = asyncio.Semaphore(self.concurrency)
        
        done = 0
        done_lock = asyncio.Lock()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=self.browser_args)
            context = await browser.new_context()

            stop_event, spinner_task = start_spinner(
                progress_label, 
                len(url_pairs), 
                lambda: done, 
                interval=0.2
            )

            async def worker(idx_pair):
                nonlocal done
                idx, (identifier, url) = idx_pair

                async with semaphore:
                    page = await context.new_page()

                    try:
                        result = await custom_fetch_func(page, identifier, url)
                        results[identifier] = result

                    finally:
                        await page.close()
                        async with done_lock:
                            done += 1

            try:
                await asyncio.gather(*[worker(item) for item in enumerate(url_pairs)])
            
            finally:
                stop_event.set()
                await spinner_task
                await browser.close()

        return results


async def scrape_urls_async(url_pairs, concurrency: int = 10, progress_label: str = "Scraping",
                           save_screenshots: bool = False, screenshot_callback=None):
    """
    Simple async scraping function
    
    Args:
        url_pairs: List of tuples (identifier, url)
        concurrency: Max concurrent pages
        progress_label: Progress label
        save_screenshots: Whether to save screenshots
        screenshot_callback: Screenshot callback function
        
    Returns:
        dict: Mapping of identifier -> html_content
    """
    scraper = AsyncScraper(concurrency=concurrency)
    return await scraper.scrape_urls(
        url_pairs, 
        progress_label=progress_label,
        save_screenshots=save_screenshots,
        screenshot_callback=screenshot_callback
    )
