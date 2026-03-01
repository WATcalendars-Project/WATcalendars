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

        # 1. Spróbuj znaleźć tabelę z nagłówkiem "Grupa/Group no."
        table_with_header = None
        for table in soup.find_all("table"):
            text = table.get_text(strip=True)
            if "Grupa/Group no." in text:
                table_with_header = table
                break

        first_td = None
        if table_with_header:
            rows = table_with_header.find_all("tr")
            if len(rows) >= 2:
                data_row = rows[1]
                tds = data_row.find_all("td")
                if tds:
                    first_td = tds[0]
                    msg = "[OK] Found first data <td> in table with 'Grupa/Group no.' header."
                    local_logs.append(msg)
                    print(msg)

        # 2. Fallback: jakby HTML był inny, użyj pierwszego <td valign="TOP">
        if not first_td:
            for td in soup.find_all("td"):
                if td.get("valign", "").upper() == "TOP":
                    first_td = td
                    msg = "[OK] Found <td valign=TOP> element (fallback)."
                    local_logs.append(msg)
                    print(msg)
                    break

        if not first_td:
            msg = "[ERROR] No suitable <td> found for WML groups."
            local_logs.append(msg)
            print(msg)
            return []

        groups = set()
        for a in first_td.find_all("a", href=True):
            href = a["href"]
            if not href.lower().endswith((".htm", ".html")):
                continue

            base = href.rsplit("/", 1)[-1].split("?")[0].split("#")[0]
            base_no_ext = re.sub(r"\.(?:htm|html)$", "", base, flags=re.IGNORECASE).strip()
            if not base_no_ext:
                continue

            token = "_".join(base_no_ext.split())
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