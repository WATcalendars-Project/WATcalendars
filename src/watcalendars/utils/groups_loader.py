import os
import json

from watcalendars import GROUPS_DIR

def load_groups(prefix: str) -> list:
    """
    Loads group names from a JSON file (e.g. ioe.json, wcy.json, etc.) in GROUPS_DIR.
    Returns a sorted list of group names.
    """
    filename = os.path.join(GROUPS_DIR, f"{prefix}_groups_url.json")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"No groups file found: {os.path.abspath(filename)}")
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data.keys())