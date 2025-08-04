# URL configuration loader for WATcalendars
# This module handles loading URLs from configuration files

from logutils import ERROR as E

# Loads a URL from the configuration based on the category and optional faculty.
# Args:
#    category: 'usos', 'groups', 'schedules', 'wat'
#    faculty: (for groups/schedules): 'wcy', 'ioe', 'wel', etc.
#    url_type: ('url', 'url_lato', 'url_zima')
# Returns:
#    Tuple (URL string, description) or (None, None) if not found
def load_url_from_config(category: str, faculty: str = None, url_type: str = 'url'):
    try:
        from config import URL_CATEGORIES
        
        # Check if category is 'usos' and return the first URL
        if category == 'usos':
            from config import USOS_URLS
            return USOS_URLS[0]['url'], USOS_URLS[0]['description']
            
        # Check if category is 'groups' or 'schedules'
        if category in URL_CATEGORIES:
            urls = URL_CATEGORIES[category]
            
            # If faculty is provided and exists
            if isinstance(urls, dict) and faculty:
                # Check if faculty exists in the dictionary
                if faculty in urls:
                    # Get the first URL for the faculty and return it
                    url_data = urls[faculty][0]
                    url = url_data.get(url_type)
                    description = url_data.get('description')
                    
                    # If URL is found, return it
                    if url:
                        return url, description
                    # If URL type is not found, return None
                    else:
                        print(f"{E} URL type '{url_type}' not found for faculty '{faculty}'")
                        return None, None
                # If faculty is not provided, return the first URL for the category
                else:
                    print(f"{E} Unknown faculty '{faculty}'")
                    return None, None
        # If category is not found, return None
        print(f"{E} Wrong category '{category}'")
        return None, None
        
    except ImportError:
        print(f"{E} Can't load config.py")
        return None, None
    except Exception as e:
        print(f"{E} {e}")
        return None, None