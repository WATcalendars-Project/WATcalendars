from logutils import OK, W, E, INFO, SpinnerContext

def load_url_from_config(category: str, faculty: str = None, url_type: str = 'url'):
    """
    Loads a URL from the configuration based on the category and optional faculty.
    
    Args:
        category: 'usos', 'groups', 'schedules', 'wat'
        faculty: (for groups/schedules): 'wcy', 'ioe', 'wel', etc.
        url_type: ('url', 'url_lato', 'url_zima')
    
    Returns:
        Tuple (URL string, description) or (None, None) if not found
    """
    try:
        from config import URL_CATEGORIES
        
        if category == 'usos':
            from config import USOS_URLS
            return USOS_URLS[0]['url'], USOS_URLS[0]['description']
            
        if category in URL_CATEGORIES:
            urls = URL_CATEGORIES[category]
            
            if isinstance(urls, dict) and faculty:
                if faculty in urls:
                    url_data = urls[faculty][0]
                    url = url_data[url_type]
                    description = url_data['description']
                    return url, description
                else:
                    print(f"{E} Unknown faculty '{faculty}'")
                    return None, None

        print(f"{E} Wrong category '{category}'")
        return None, None
        
    except ImportError:
        print(f"{E} Can't load config.py")
        return None, None
    except Exception as e:
        print(f"{E} {e}")
        return None, None
    
def test_connection_with_monitoring(url: str, description: str = None):
    """Testing + logging all HTTP requests"""

    from playwright.sync_api import sync_playwright, Request, Response
    import time

    display_name = description if description else url

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Counters for summary
        request_count = 0
        response_count = 0
        total_bytes = 0

        def log_request(request: Request):
            nonlocal request_count
            request_count += 1
            headers = dict(request.headers)
            print(f"→ {request.method} {request.url} (Headers: {len(headers)} items)")

        def log_response(response: Response):
            nonlocal response_count, total_bytes
            response_count += 1
            try:
                body = response.body()
                size = len(body) if body else 0
                total_bytes += size
                print(f"← {response.status} {response.url} ({size} bytes)")
            except Exception:
                print(f"← {response.status} {response.url} (size unknown)")

        page.on("request", log_request)
        page.on("response", log_response)

        try:
            print(f"Checking connection to {display_name}...")
            print(f"{INFO} URL: {url}")
            start_time = time.time()
            
            # Spinner during page loading
            with SpinnerContext("Loading"):
                page.goto(url)
            
            duration = time.time() - start_time
            browser.close()
            
            # Summary before OK log
            if total_bytes > 1024 * 1024:
                size_str = f"{total_bytes / (1024 * 1024):.1f} MB"
            elif total_bytes > 1024:
                size_str = f"{total_bytes / 1024:.1f} KB"
            else:
                size_str = f"{total_bytes} bytes"
            
            print(f"{INFO} Summary: {request_count} requests, {response_count} responses, {size_str} received")
            print(f"{OK} Connection successful to {display_name} in {duration:.2f}s")
        
        except Exception as e:
            browser.close()
            print(f"{E} Failed to connect to {display_name}: {e}")