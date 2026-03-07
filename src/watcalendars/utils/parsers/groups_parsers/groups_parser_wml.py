import re

from bs4 import BeautifulSoup


def parse_wml_groups(html, logs=None):
    """Parse WML group names from HTML content.

    Struktura strony (wg podanego HTML):
    - tabela z nagłówkiem "Grupa/Group no." w pierwszym wierszu
    - w drugim wierszu trzy kolumny (td): grupy, prowadzący, sale
    Bierzemy TYLKO pierwszą kolumnę po nagłówku.
    Zwracamy posortowaną listę tokenów grup (bez rozszerzenia, spacje -> _).
    """

    def parse_wml_groups_log():
        local_logs = []
        if not html:
            msg = "[ERROR] No HTML retrieved."
            local_logs.append(msg)
            print(msg)
            return []

        soup = BeautifulSoup(html, "html.parser")

        # 0. First try the same strategy as other parsers (gro/pod/a elements)
        gro_tags = soup.find_all(['gro', 'pod', 'a'])
        if gro_tags:
            msg = f"[OK] Found {len(gro_tags)} <gro>/<pod>/<a> elements (WLO-like fallback)."
            local_logs.append(msg)
            print(msg)
            anchor_parent = gro_tags

        # 1. Try to find common patterns in order of likelihood
        #    a) div#container > ul.menu (observed in devtools screenshot)
        #    b) table with header containing "Grupa/Group no." (original approach)
        #    c) first <td valign="TOP"> (fallback)
        # anchor_parent may already be set by gro_tags above

        # a) div#container > ul.menu
        container = soup.find("div", id="container")
        if container:
            ul = container.find("ul", class_="menu")
            if ul:
                anchor_parent = ul
                msg = "[OK] Found div#container > ul.menu (preferred)."
                local_logs.append(msg)
                print(msg)

        # b) table with header
        if not anchor_parent:
            for table in soup.find_all("table"):
                text = table.get_text(strip=True)
                if "Grupa/Group no." in text:
                    rows = table.find_all("tr")
                    if len(rows) >= 2:
                        data_row = rows[1]
                        tds = data_row.find_all("td")
                        if tds:
                            anchor_parent = tds[0]
                            msg = "[OK] Found first data <td> in table with 'Grupa/Group no.' header."
                            local_logs.append(msg)
                            print(msg)
                    break

        # c) fallback: first <td valign="TOP">
        if not anchor_parent:
            for td in soup.find_all("td"):
                if td.get("valign", "").upper() == "TOP":
                    anchor_parent = td
                    msg = "[OK] Found <td valign=TOP> element (fallback)."
                    local_logs.append(msg)
                    print(msg)
                    break

        if not anchor_parent:
            msg = "[ERROR] No suitable anchor parent found for WML groups."
            local_logs.append(msg)
            print(msg)
            # Global fallback: try to find any links in the whole document
            msg = "[WARN] Falling back to scanning all <a> elements in the document."
            local_logs.append(msg)
            print(msg)
            anchor_parent = soup  # scan entire document below

        groups = set()
        # If anchor_parent is a list (gro_tags), iterate over elements directly
        anchors = []
        if isinstance(anchor_parent, list):
            for el in anchor_parent:
                if el.name == 'a' and el.get('href'):
                    anchors.append(el)
                else:
                    anchors.extend(el.find_all('a', href=True))
        else:
            anchors = anchor_parent.find_all('a', href=True)

        for a in anchors:
            href = a["href"]
            # Keep only typical HTML pages
            if not href.lower().endswith((".htm", ".html")):
                continue

            base = href.rsplit("/", 1)[-1].split("?")[0].split("#")[0]
            base_no_ext = re.sub(r"\.(?:htm|html)$", "", base, flags=re.IGNORECASE).strip()
            if not base_no_ext:
                continue

            # Apply WLO-like filtering: prefer names starting with WML
            teacher_pattern = r'^_?(mgr|dr|prof|plk|pplk|mjr|kpt|por|inz|chor|ml\._chor)\b'
            room_pattern = r'^(s\d+|n\d+|aula|bibl|hala|sala|\d{1,3}(?:\.\d+)*_[0-9A-Za-z]+)$'

            if not re.match(r'^WML', base_no_ext, re.IGNORECASE):
                if re.match(teacher_pattern, base_no_ext, re.IGNORECASE):
                    continue
                if re.match(room_pattern, base_no_ext, re.IGNORECASE):
                    continue
                # If it doesn't start with WML, allow K- or alphanumeric tokens as groups too
                # (but skip obvious rooms/teachers)

            # Normalize token: remove non-alphanumeric characters so K-8103093 -> K8103093
            token = re.sub(r"[^A-Za-z0-9]+", "", base_no_ext)
            if not token:
                continue
            groups.add(token)

        if groups:
            msg = f"[OK] Extracted {len(groups)} WML group links."
            local_logs.append(msg)
            print(msg)
        else:
            msg = "[WARN] No WML group links found in selected <td>."
            local_logs.append(msg)
            print(msg)

        if logs is not None:
            logs.extend(local_logs)
        return sorted(groups)

    print("Parsing HTML content for WML groups...")
    groups = parse_wml_groups_log()
    return groups