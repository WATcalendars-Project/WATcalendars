# URL configuration loader for WATcalendars
# This module handles loading URLs from configuration files

from logutils import ERROR as E, INFO

PREFERRED_ORDER = ["url", "url_lato", "url_zima"]

def _pick_url(url_data, requested):
    # Exact if present
    if requested in url_data and url_data.get(requested):
        return url_data.get(requested)
    # Fallback in preferred order
    for k in PREFERRED_ORDER:
        if k in url_data and url_data.get(k):
            return url_data.get(k)
    return None

# Loads a URL from the configuration based on the category and optional faculty.
# Args:
#    category: 'usos', 'groups', 'schedules', 'wat'
#    faculty: (for groups/schedules): 'wcy', 'ioe', 'wel', etc.
#    url_type: ('url', 'url_lato', 'url_zima')
# Returns:
#    Tuple (URL string, description) or (None, None) if not found
def load_url_from_config(category: str, faculty: str = None, url_type: str = 'url'):
    try:
        from config import URL_CATEGORIES, USOS_URLS
        # usos shortcut
        if category == 'usos':
            return USOS_URLS[0]['url'], USOS_URLS[0]['description']

        if category not in URL_CATEGORIES:
            print(f"{E} Wrong category '{category}'")
            return None, None

        urls = URL_CATEGORIES[category]

        # Dict form (groups / schedules)
        if isinstance(urls, dict):
            if not faculty:
                print(f"{E} Faculty required for category '{category}'")
                return None, None
            fac_norm = faculty.lower().strip()
            # Build case-insensitive map with stripped keys
            ci_map = {k.lower().strip(): k for k in urls.keys()}
            if fac_norm not in ci_map:
                print(f"{E} Unknown faculty '{faculty}'. Available: {', '.join(sorted(k.strip() for k in urls.keys()))}")
                return None, None
            real_key = ci_map[fac_norm]
            url_list = urls[real_key]
            if not url_list:
                print(f"{E} No entries for faculty '{faculty}'")
                return None, None
            url_data = url_list[0]
            picked = _pick_url(url_data, url_type)
            if not picked:
                print(f"{E} No URL found (requested '{url_type}') for faculty '{faculty}'. Keys present: {', '.join(url_data.keys())}")
                return None, None
            return picked, url_data.get('description')

        # List form (should only be usos already handled)
        print(f"{E} Unsupported URL structure for category '{category}'")
        return None, None
    except ImportError:
        print(f"{E} Can't load config.py")
        return None, None
    except Exception as e:
        print(f"{E} {e}")
        return None, None