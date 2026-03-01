import re

from watcalendars.utils.logutils import log_entry, log, SUCCESS, WARNING, ERROR, OK
from bs4 import BeautifulSoup

def parse_wlo_groups(html, logs=None):
    """
    Parse WLO group names from HTML content.
    Returns sorted list of group tokens.
    """

    def parse_wlo_groups_log():
        logs = []
        if not html:
            log_entry(f"{ERROR} No HTML retrieved.", logs)
            return []

        soup = BeautifulSoup(html, 'html.parser')
        
        gro_tags = soup.find_all('gro')
        if not gro_tags:
            log_entry(f"{ERROR} No <gro> tags found.", logs)
            return []
            
        log_entry(f"{OK} Found <gro> elements.", logs)

        groups = set()
        for gro in gro_tags:
            href = gro.get('href', '')
            if not href.lower().endswith(('.htm', '.html')):
                continue
            base = href.rsplit('/', 1)[-1].split('?')[0].split('#')[0]
            base_no_ext = re.sub(r'\.(?:htm|html)$', '', base, flags=re.IGNORECASE).strip()
            if not base_no_ext:
                continue
            token = '_'.join(base_no_ext.split())
            groups.add(token)
            
        log_entry("Extracting group links from <gro> elements.", logs)
        return sorted(groups)

    groups = log("Parsing HTML content for WLO groups...", parse_wlo_groups_log)
    return sorted(groups)
