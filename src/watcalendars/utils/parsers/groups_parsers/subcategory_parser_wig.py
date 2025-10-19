from watcalendars.utils.logutils import log_entry, log, SUCCESS, WARNING, ERROR, OK
from bs4 import BeautifulSoup

def parse_wig_subcategories(html, logs=None):
    """
    Parse WIG subcategory URLs from HTML content.
    Looks for span elements with class 'pd-subcategory' and finds sibling <a> links.
    Returns dict of {subcategory_name: url}.
    """

    def parse_wig_subcategories_log():
        logs = []
        if not html:
            log_entry(f"{ERROR} No HTML retrieved.", logs)
            return {}

        soup = BeautifulSoup(html, "html.parser")
        
        # Find all span elements with class="pd-subcategory"
        subcategory_spans = soup.find_all("span", class_="pd-subcategory")
        log_entry(f"{OK} Found {len(subcategory_spans)} subcategory elements.", logs)
        
        subcategories = {}
        for span in subcategory_spans:
            # The link is a sibling of the span, inside the same parent <li>
            parent = span.parent
            if parent:
                link = parent.find("a")
                if link and link.get("href"):
                    href = link.get("href")
                    name = link.text.strip()
                    
                    # Build full URL if relative
                    if href.startswith("/"):
                        base_url = "https://www.wig.wat.edu.pl"
                        full_url = base_url + href
                    elif not href.startswith("http"):
                        base_url = "https://www.wig.wat.edu.pl/cpp/index.php/studenci/plany-rozklady-terminy/rozklady-zajec"
                        full_url = f"{base_url}/{href}"
                    else:
                        full_url = href
                    
                    if name:
                        subcategories[name] = full_url
        
        log_entry(f"Parsed {len(subcategories)} subcategories.", logs)
        return subcategories

    subcategories = log("Parsing HTML content for WIG subcategories...", parse_wig_subcategories_log)
    return subcategories
