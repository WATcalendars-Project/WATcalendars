# Tests the connection to a URL with monitoring and logging
# Use Playwright to monitor the connection
# sync_playwright is used for synchronous execution
# requests and responses are logged

from logutils import OK, ERROR as E, GET, RESPONSE, log_entry, log
from playwright.sync_api import sync_playwright, Request, Response
import time


def test_connection_with_monitoring(url: str, description: str = None):
    display_name = description if description else url
    request_count = 0
    response_count = 0 
    total_bytes = 0
    logs = []

    def perform_connection_test():
        nonlocal request_count, response_count, total_bytes, logs
    
        print(f"URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            def log_request(request: Request):
                nonlocal request_count
                request_count += 1
                current_request_count = request_count
                log_entry(f"{GET} {request.method}:{current_request_count} {request.url}", logs)

            def log_response(response: Response):
                nonlocal response_count, total_bytes
                response_count += 1
                current_response_count = response_count
                
                try:
                    body = response.body()
                    size = len(body) if body else 0
                    total_bytes += size

                    if size > 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    elif size > 1024:
                        size_str = f"{size / 1024:.1f} kB"
                    else:
                        size_str = f"{size} B"
                    
                    log_entry(f"{RESPONSE} {response.status}:{current_response_count} {response.url} [{size_str}]", logs)

                except Exception:
                    log_entry(f"{RESPONSE} {response.status}:{current_response_count} {response.url} [size unknown]", logs)


            page.on("request", log_request)
            page.on("response", log_response)


            try:
                start_time = time.time()
                page.goto(url)     
                duration = time.time() - start_time
                browser.close()
                return duration
                
            except Exception as e:
                browser.close()
                raise e
    
    try:
        duration = log(f"Checking connection to ({display_name})...", perform_connection_test)
        
        if total_bytes > 1024 * 1024:
            total_size_str = f"{total_bytes / (1024 * 1024):.1f} MB"
        elif total_bytes > 1024:
            total_size_str = f"{total_bytes / 1024:.1f} kB"
        else:
            total_size_str = f"{total_bytes} B"

        speed_size = total_bytes / duration
        speed = f"{speed_size / 1024:.1f} kB/s" if speed_size > 1024 else f"{speed_size:.1f} B/s"

        print(f"{OK} Connection successful.")
        print(f"Summary: {request_count} requests, {response_count} responses")
        print(f"Received {total_size_str} in {duration:.2f}s ({speed})\n")
    
    except Exception as e:
        print(f"{E} Failed to connect to {display_name}: {e}")