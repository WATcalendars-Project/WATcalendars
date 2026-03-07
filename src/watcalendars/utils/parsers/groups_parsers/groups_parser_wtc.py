import re

from bs4 import BeautifulSoup
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS

def parse_wtc_groups(html, logs=None):
    """
    Parse WTC group names from HTML content.
    Returns sorted list of group tokens.
    """

    def parse_wtc_groups_log():
        logs = []
        if not html:
            logs.append(f"{ERROR} No HTML retrieved."); print(f"{ERROR} No HTML retrieved.")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        first_td = None
        for td in soup.find_all('td'):
            if td.get('valign', '').upper() == 'TOP':
                first_td = td
                logs.append(f"{OK} Found <td valign=TOP> element."); print(f"{OK} Found <td valign=TOP> element.")
                break
        if not first_td:
            logs.append(f"{ERROR} No <td valign=TOP> found."); print(f"{ERROR} No <td valign=TOP> found.")
            return []

        groups = set()
        for a in first_td.find_all('a', href=True):
            href = a['href']
            base = href.rsplit('/', 1)[-1].split('?')[0].split('#')[0]
            base_no_ext = re.sub(r'\.[a-zA-Z0-9]+$', '', base).strip()
            if not base_no_ext:
                continue
            token = '_'.join(base_no_ext.split())
            if len(token) >= 3:
                groups.add(token)
        logs.append(f"Extracting group links from <td> element."); print(f"Extracting group links from <td> element.")
        return sorted(groups)

    groups = (print("Parsing HTML content for WTC groups..."), parse_wtc_groups_log())[1]
    return sorted(groups)