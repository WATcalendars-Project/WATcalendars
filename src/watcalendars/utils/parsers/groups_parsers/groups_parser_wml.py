import re

from bs4 import BeautifulSoup

def parse_wml_groups(html, logs=None):
    """
    Parse WML group names from HTML content.
    Returns sorted list of group tokens.
    """

    def parse_wml_groups_log():
        logs = []
        if not html:
            logs.append(f"[ERROR] No HTML retrieved."); print(f"[ERROR] No HTML retrieved.")
            return []

        soup = BeautifulSoup(html, 'html.parser')
        first_td = None
        for td in soup.find_all('td'):
            if td.get('valign', '').upper() == 'TOP':
                first_td = td
                logs.append(f"[OK] Found <td valign=TOP> element."); print(f"[OK] Found <td valign=TOP> element.")
                break
        if not first_td:
            logs.append(f"[ERROR] No <td valign=TOP> found."); print(f"[ERROR] No <td valign=TOP> found.")
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
        logs.append("Extracting group links from <td> element."); print("Extracting group links from <td> element.")
        return sorted(groups)

    groups = (print("Parsing HTML content for WML groups..."), parse_wml_groups_log())[1]
    return sorted(groups)