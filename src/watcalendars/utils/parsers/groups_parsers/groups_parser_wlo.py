import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def parse_wlo_groups(html, logs=None):
    """
    Parse WLO group names from HTML content.
    Returns sorted list of group tokens.
    """

    def parse_wlo_groups_log():
        logs = []
        if not html:
            logs.append(f"[ERROR] No HTML retrieved."); print(f"[ERROR] No HTML retrieved.")
            return []

        soup = BeautifulSoup(html, 'html.parser')

        # Szukamy zarówno tagów <gro> (grupy) jak i <pod> (podgrupy) oraz ewentualnie <a>, jeśli XSLT przetworzył dokument
        gro_tags = soup.find_all(['gro', 'pod', 'a'])
        if not gro_tags:
            logs.append(f"[ERROR] No <gro>, <pod> or <a> tags found."); print(f"[ERROR] No <gro>, <pod> or <a> tags found.")
            return []

        logs.append(f"[OK] Found {len(gro_tags)} <gro>/<pod>/<a> elements."); print(f"[OK] Found {len(gro_tags)} <gro>/<pod>/<a> elements.")

        groups = set()
        for gro in gro_tags:
            href = gro.get('href', '')
            if not href.lower().endswith(('.htm', '.html')):
                continue
            
            base = href.rsplit('/', 1)[-1].split('?')[0].split('#')[0]
            base_no_ext = re.sub(r'\.(?:htm|html)$', '', base, flags=re.IGNORECASE).strip()
            if not base_no_ext:
                continue
                
            # Odsianie linków bezpośrenio do planów wykładowców (zwykle n<liczba>.htm) i sal (s<liczba>.htm)
            # W przypadku tagów <a> mogą się pojawić, dlatego trzeba uważać
            if gro.name == 'a' and re.match(r'^[ns]\d+$', base_no_ext, re.IGNORECASE):
                continue
                
            token = '_'.join(base_no_ext.split())
            groups.add(token)

        logs.append(f"Extracting group links from {len(gro_tags)} elements."); print(f"Extracting group links from {len(gro_tags)} elements.")
        return sorted(groups)

    groups = (print("Parsing HTML content for WLO groups..."), parse_wlo_groups_log())[1]
    return sorted(groups)
