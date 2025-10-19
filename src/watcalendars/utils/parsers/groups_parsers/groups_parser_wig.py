from watcalendars.utils.logutils import log_entry, log, SUCCESS, WARNING, ERROR, OK
from bs4 import BeautifulSoup

def parse_wig_groups_from_subcategory(html, logs=None):
    """
    Parse WIG group schedule links from a subcategory page.
    Looks for <div class="pd-float"> containing <a> links to Word documents.
    Returns dict of {group_name: download_url}.
    """

    def parse_wig_groups_log():
        logs = []
        if not html:
            log_entry(f"{ERROR} No HTML retrieved.", logs)
            return {}

        soup = BeautifulSoup(html, "html.parser")
        
        float_divs = soup.find_all("div", class_="pd-float")
        log_entry(f"{OK} Found {len(float_divs)} pd-float divs.", logs)
        
        groups = {}
        for div in float_divs:
            link = div.find("a")
            if link and link.get("href"):
                href = link.get("href")
                group_name = link.text.strip()
                
                if href.startswith("/"):
                    base_url = "https://www.wig.wat.edu.pl"
                    full_url = base_url + href
                elif not href.startswith("http"):
                    base_url = "https://www.wig.wat.edu.pl/cpp/index.php"
                    full_url = f"{base_url}/{href}"
                else:
                    full_url = href
                
                if group_name:
                    groups[group_name] = full_url
        
        log_entry(f"Parsed {len(groups)} groups.", logs)
        return groups

    groups = log("Parsing HTML content for WIG groups...", parse_wig_groups_log)
    return groups