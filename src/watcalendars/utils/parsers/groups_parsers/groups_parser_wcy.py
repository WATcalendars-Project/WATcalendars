import re

from watcalendars.utils.logutils import log_entry, log, SUCCESS, WARNING, ERROR, OK
from bs4 import BeautifulSoup

def parse_wcy_groups(html, logs=None):
    """
    Parse WCY group names from HTML content (option elements).
    Returns sorted list of group tokens.
    """

    def parse_wcy_groups_log():
        logs = []
        if not html:
            log_entry(f"{ERROR} No HTML retrieved.", logs)
            return []

        soup = BeautifulSoup(html, "html.parser")
        options = soup.find_all("option")
        log_entry(f"{OK} Found pagination element: {len(options)} options.", logs)
        groups = []
        for option in options:
            group = option.text.strip()
            if group and "- Wybierz grupę -" not in group:
                group = group.rstrip(".")
                groups.append(group)
        log_entry(f"Founding groups.", logs)
        return sorted(groups)

    groups = log("Parsing HTML content for WCY groups...", parse_wcy_groups_log)
    return sorted(groups)