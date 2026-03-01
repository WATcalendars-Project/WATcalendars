import os
import json

from watcalendars import GROUPS_DIR


def load_groups(prefix: str) -> list:
    """Load group names for given faculty prefix.

    Supports both legacy flat files:
      db/groups_url/{prefix}_groups_url.json
    and new per-faculty subdirs:
      db/groups_url/{prefix}_groups_url/*json

    If multiple JSON files exist in the subdir (e.g. lato/zima),
    the function prefers files containing "lato" in the name,
    then "zima", otherwise the first one in sorted order.
    """

    base_name = f"{prefix}_groups_url.json"
    direct_path = os.path.join(GROUPS_DIR, base_name)

    if os.path.isfile(direct_path):
        filename = direct_path
    else:
        dir_path = os.path.join(GROUPS_DIR, f"{prefix}_groups_url")
        if not os.path.isdir(dir_path):
            raise FileNotFoundError(
                f"No groups file found for prefix '{prefix}' in {os.path.abspath(GROUPS_DIR)}"
            )

        candidates = [f for f in os.listdir(dir_path) if f.lower().endswith(".json")]
        if not candidates:
            raise FileNotFoundError(
                f"No JSON groups files found in {os.path.abspath(dir_path)} for prefix '{prefix}'"
            )

        candidates_sorted = sorted(candidates)
        preferred = None
        for hint in ("lato", "zima"):
            for name in candidates_sorted:
                if hint in name.lower():
                    preferred = name
                    break
            if preferred:
                break

        if not preferred:
            preferred = candidates_sorted[0]

        filename = os.path.join(dir_path, preferred)

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    return sorted(data.keys())