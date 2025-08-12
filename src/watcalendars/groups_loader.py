# groups data loader for WATcalendars
import os
import re
from logutils import ERROR as E

script_dir = os.path.dirname(os.path.abspath(__file__))
_groups_dir = os.path.join(script_dir, "..", "..", "db", "groups")
_new_marker_pattern = re.compile(r"\s+\[NEW\]$")

__all__ = ["load_groups", "get_groups_from_file"]


def load_groups(faculty: str):
    """Zwraca listę grup dla wydziału (bez znaczników [NEW]).
    Jeśli plik nie istnieje -> zwraca pustą listę.
    """
    path = os.path.join(_groups_dir, f"{faculty.lower()}.txt")
    if not os.path.exists(path):
        print(f"{E} Groups file for '{faculty}' not found: {os.path.abspath(path)}")
        return []
    groups = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                line = _new_marker_pattern.sub('', line)
                groups.append(line)
    except Exception as exc:
        print(f"{E} {exc}")
        return []
    seen = set()
    dedup = []
    for g in groups:
        if g not in seen:
            seen.add(g)
            dedup.append(g)
    return dedup

def get_groups_from_file(faculty: str):
    return load_groups(faculty)