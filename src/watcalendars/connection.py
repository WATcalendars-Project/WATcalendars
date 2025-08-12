from logutils import OK, ERROR as E, GET, RESPONSE, log_entry, log
from playwright.sync_api import sync_playwright, Request, Response
import time

# Tests the connection to a URL with monitoring and logging
def test_connection_with_monitoring(url: str, description: str = None):
    # Use Playwright to monitor the connection
    # sync_playwright is used for synchronous execution
    # requests and responses are logged
    # Display name for the URL, using description (description from config) if available
    display_name = description if description else url

    # Counters for summary
    request_count = 0
    response_count = 0 
    total_bytes = 0
    
    # Storage for logs that will be displayed after spinner completes
    logs = []

    def perform_connection_test():
        nonlocal request_count, response_count, total_bytes, logs
        
        # Print initial info
        print(f"URL: {url}")
        
        with sync_playwright() as p:
            # Launch a browser instance
            # Using Chromium for better compatibility with most websites
            browser = p.chromium.launch()
            # Create a new page in the browser
            # This page will be used to navigate to the URL and monitor requests/responses
            page = browser.new_page()

            def log_request(request: Request):
                # Log the request details
                nonlocal request_count
                request_count += 1
                current_request_count = request_count  # Capture current count

                log_entry(f"{GET} {request.method}:{current_request_count} {request.url}", logs)

            def log_response(response: Response):
                # Log the response details
                nonlocal response_count, total_bytes
                response_count += 1
                current_response_count = response_count  # Capture current count
                
                try:
                    # Get the response body size
                    body = response.body()
                    # If body is None, size is 0
                    # Use len(body) to get the size of the response body
                    size = len(body) if body else 0
                    total_bytes += size

                    # Format the size for display
                    if size > 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    elif size > 1024:
                        size_str = f"{size / 1024:.1f} kB"
                    else:
                        size_str = f"{size} B"
                    
                    log_entry(f"{RESPONSE} {response.status}:{current_response_count} {response.url} [{size_str}]", logs)

                # If there's an error getting the body, print the status and URL
                except Exception:
                    log_entry(f"{RESPONSE} {response.status}:{current_response_count} {response.url} [size unknown]", logs)

            # Attach request and response logging
            page.on("request", log_request)
            page.on("response", log_response)

            # Start the connection test
            try:
                start_time = time.time()
                
                # Navigate to URL
                page.goto(url)
                
                duration = time.time() - start_time
                browser.close()
                
                return duration
                
            except Exception as e:
                browser.close()
                raise e
    
    try:
        # Use the log function with spinner
        duration = log(f"Checking connection to ({display_name})...", perform_connection_test)
        
        # Summary
        if total_bytes > 1024 * 1024:
            total_size_str = f"{total_bytes / (1024 * 1024):.1f} MB"
        elif total_bytes > 1024:
            total_size_str = f"{total_bytes / 1024:.1f} kB"
        else:
            total_size_str = f"{total_bytes} B"

        # Calculate speed
        speed_size = total_bytes / duration
        speed = f"{speed_size / 1024:.1f} kB/s" if speed_size > 1024 else f"{speed_size:.1f} B/s"

        # Print the summary of requests, responses, and total size
        print(f"{OK} Connection successful.")
        print(f"Summary: {request_count} requests, {response_count} responses")
        print(f"Received {total_size_str} in {duration:.2f}s ({speed})")
    
    except Exception as e:
        print(f"{E} Failed to connect to {display_name}: {e}")