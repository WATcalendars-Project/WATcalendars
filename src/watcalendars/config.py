# Servers URL's configuration for the WatCalendars application.

# Main USOS URL's
USOS_URLS = [
    {
        'url': 'https://usos.wat.edu.pl/kontroler.php?_action=katalog2/osoby/pracownicyJednostki&jed_org_kod=A000000',
        'description': 'USOS server - employees'
    }
]

# URL-e for groups
GROUP_URLS = {
    'ioe': [
        {
            'url_lato': 'https://ioe.wat.edu.pl/plany/lato/index.xml',
            'description': 'IOE groups'
        }
    ],
    'wcy': [
        {
            'url': 'https://planzajec.wcy.wat.edu.pl/rozklad',
            'description': 'WCY groups'
        }
    ],
    'wel': [
        {
            'url_lato': 'https://plany.wel.wat.edu.pl/lato/index.xml',
            'description': 'WEL groups'
        }
    ],
    """
    'wig': [
        {
            'url': '',
            'description': 'WIG groups'
        }
    ],
    """
    'wim': [
        {
            'url_lato': 'https://www.wim.wat.edu.pl/wp-content/uploads/rozklady/lato/index.xml',
            'description': 'WIM groups'
        }
    ],
    'wlo': [
        {
            'url_lato': 'https://wlo.wat.edu.pl/planzajec/letni/index.xml',
            'description': 'WLO groups'
        }
    ],
    'wml': [
        {
            'url': 'https://wml.wat.edu.pl/rozklady-zajec/',
            'description': 'WML groups'
        }
    ],
    'wtc': [
        {
            'url': 'https://www.wtc.wat.edu.pl/Plany/index.xml',
            'description': 'WTC groups'
        }
    ],
}

# URL's for faculties - harmonograms
SCHEDULE_URLS = {
    'ioe': [
        {
            'url_lato': 'https://ioe.wat.edu.pl/plany/lato/{group}.htm',
            'description': 'IOE {group} schedule'
        }
    ],
    'wcy': [
        {
            'url': 'https://planzajec.wcy.wat.edu.pl/pl/rozklad?grupa_id={group}',
            'description': 'WCY {group} schedule'
        }
    ],
    'wel': [
        {
            'url_lato': 'https://plany.wel.wat.edu.pl/lato/{group}.htm',
            'description': 'WEL {group} schedule'
        }
    ],
    """
    'wig': [
        {
            'url': '',
            'description': 'WIG {group} schedule'
        }
    ],
    """
    'wim': [
        {
            'url_lato': 'https://www.wim.wat.edu.pl/wp-content/uploads/rozklady/lato/{group}.htm',
            'description': 'WIM {group} schedule'
        }
    ],
    'wlo': [
        {
            'url_lato': 'https://wlo.wat.edu.pl/planzajec/letni/{group}.htm',
            'description': 'WLO {group} schedule'
        }
    ],
    """
    'wml': [
        {
            'url': 'https://wml.wat.edu.pl/rozklady-zajec/',
            'description': 'WML {group} schedule'
        }
    ],
    """
    'wtc': [
        {
            'url': 'https://www.wtc.wat.edu.pl/Plany/{group}.htm',
            'description': 'WTC {group} schedule'
        }
    ]
}

# URL Categories for easier access in connection.py and ...
URL_CATEGORIES = {
    'schedules': SCHEDULE_URLS,
    'groups': GROUP_URLS,
    'usos': [{'url': USOS_URLS[0]['url'], 'description': USOS_URLS[0]['description']}]
}