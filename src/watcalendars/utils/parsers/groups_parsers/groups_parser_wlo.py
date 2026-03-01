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

        # Pattern to identify and exclude teachers (na wszelki wypadek)
        teacher_pattern = r'^_?(mgr|dr|prof|plk|pplk|mjr|kpt|por|inz|chor|ml\._chor)\b'
        # Pattern to identify i wykluczyć oczywiste sale / lokalizacje
        room_pattern = r'^(s\d+|n\d+|aula|bibl|hala|sala|\d{1,3}(?:\.\d+)*_[0-9A-Za-z]+)$'

        for gro in gro_tags:
            href = gro.get('href', '')
            if not href.lower().endswith(('.htm', '.html')):
                continue
            
            base = href.rsplit('/', 1)[-1].split('?')[0].split('#')[0]
            base_no_ext = re.sub(r'\.(?:htm|html)$', '', base, flags=re.IGNORECASE).strip()
            if not base_no_ext:
                continue

            # Interesują nas wyłącznie właściwe grupy WLO –
            # na stronie mają one nazwy zaczynające się od "WLO".
            # Dzięki temu od razu odcinamy sale (np. "3.16_135")
            # oraz pliki prowadzących.
            if not re.match(r'^WLO', base_no_ext, re.IGNORECASE):
                # Dodatkowo odrzucamy typowe wzorce sal i prowadzących
                if re.match(teacher_pattern, base_no_ext, re.IGNORECASE):
                    continue
                if re.match(room_pattern, base_no_ext, re.IGNORECASE):
                    continue
                # wszystko inne bez prefiksu WLO traktujemy jako nie‑grupy
                continue

            token = '_'.join(base_no_ext.split())
            groups.add(token)

        logs.append(f"Extracting group links from {len(gro_tags)} elements."); print(f"Extracting group links from {len(gro_tags)} elements.")
        return sorted(groups)

    groups = (print("Parsing HTML content for WLO groups..."), parse_wlo_groups_log())[1]
    return sorted(groups)
