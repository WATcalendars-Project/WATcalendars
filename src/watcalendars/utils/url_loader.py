# URL configuration loader for WATcalendars
# This module handles loading URLs from configuration files
# Usage:
# For example: load_url_from_config(wcy_schedule, url_lato)

from watcalendars.utils.logutils import ERROR as E, INFO
from watcalendars.utils.config import URL


def _pick_url(url_data, requested):
    if requested in url_data and url_data.get(requested):
        return url_data.get(requested)
    return None


def load_url_from_config(key: str, url_type: str = None):
    try:
        if not url_type:
            print(f"{E} url_type must be specified explicitly.")
            return None, None

        if isinstance(URL, dict):
            if key not in URL:
                available_keys = [k for k in URL.keys() if k != 'usos']
                print(f"{E} Unknown key '{key}'. Available: {', '.join(sorted(available_keys))}")
                return None, None

            url_list = URL[key]
            if not url_list:
                print(f"{E} No entries for key '{key}'")
                return None, None

            url_data = url_list[0]
            picked = _pick_url(url_data, url_type)
            if not picked:
                print(f"{E} No URL found (requested '{url_type}') for key '{key}'. Keys present: {', '.join(url_data.keys())}")
                return None, None
            return picked, url_data.get('description')

        print(f"{E} Unsupported URL structure")
        return None, None

    except ImportError:
        print(f"{E} Can't load config.py")
        return None, None

    except Exception as e:
        print(f"{E} {e}")
        return None, None