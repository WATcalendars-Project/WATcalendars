import re

from bs4 import BeautifulSoup
from watcalendars.utils.log import OK, ERROR, WARNING, INFO, SUCCESS

def parse_wel_groups(html, logs=None):
    """
    Parse WEL group names from HTML content.
    Returns sorted list of group tokens.
    """

    def parse_wel_groups_log():
        logs = []
        if not html:
            logs.append(f"{ERROR} No HTML retrieved."); print(f"{ERROR} No HTML retrieved.")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        tds = [td for td in soup.find_all('td') if td.get('valign', '').upper() == 'TOP']
        
        if not tds:
            logs.append(f"{ERROR} No <td valign=TOP> found."); print(f"{ERROR} No <td valign=TOP> found.")
            return []
            
        logs.append(f"{OK} Found {len(tds)} <td valign=TOP> elements. Proceeding with the first one (Groups)."); print(f"{OK} Found {len(tds)} <td valign=TOP> elements. Proceeding with the first one (Groups).")

        groups = set()
        first_td = tds[0]
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
        logs.append(f"Extracting group links from first <td> element."); print(f"{INFO} Extracting group links from first <td> element.")
        return sorted(groups)

    groups = (print("Parsing HTML content for WEL groups..."), parse_wel_groups_log())[1]
    return sorted(groups)