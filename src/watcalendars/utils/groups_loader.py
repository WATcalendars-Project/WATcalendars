# groups data loader for WATcalendars
# This module handles loading groups names for scraping calendars
# Usage:
# groups = load_groups("wcy")

import os
from watcalendars.utils.logutils import ERROR as E
from watcalendars import GROUPS_DIR

def load_groups(faculty: str):
    path = os.path.join(GROUPS_DIR, f"{faculty.lower()}.txt")

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

                group = line.replace(' [NEW]', '').strip()

                if group and group not in groups:
                    groups.append(group)

    except Exception as exc:
        print(f"{E} {exc}")
        return []

    return groups


def get_groups_from_file(faculty: str):
    return load_groups(faculty)