import re

from watcalendars.utils.logutils import log_entry, log, SUCCESS, WARNING, ERROR, OK
from bs4 import BeautifulSoup

def parse_wim_groups(html, logs=None):
    """
    Parse WIM group names from HTML content.
    Returns sorted list of group tokens.
    """

    def parse_wim_groups_log():
        logs = []
        if not html:
            log_entry(f"{ERROR} No HTML retrieved.", logs)
            return []

        soup = BeautifulSoup(html, 'html.parser')
        first_td = None
        for td in soup.find_all('td'):
            if td.get('valign', '').upper() == 'TOP':
                first_td = td
                log_entry(f"{OK} Found <td valign=TOP> element.", logs)
                break
        if not first_td:
            log_entry(f"{ERROR} No <td valign=TOP> found.", logs)
            return []

        groups = set()
        for a in first_td.find_all('a', href=True):
            href = a['href']
            if not href.lower().endswith(('.htm', '.html')):
                continue
            base = href.rsplit('/', 1)[-1].split('?')[0].split('#')[0]
            base_no_ext = re.sub(r'\.(?:htm|html)$', '', base, flags=re.IGNORECASE).strip()
            if not base_no_ext:
                continue
            token = '_'.join(base_no_ext.split())
            groups.add(token)
        log_entry("Extracting group links from <td> element.", logs)
        return sorted(groups)

    groups = log("Parsing HTML content for WIM groups...", parse_wim_groups_log)
    return sorted(groups)