import re
# Servers URL's configuration for the WATcalendars application.

############################## URL'S ##############################
URL = {
    'usos': [
        {
            'url': 'https://usos.wat.edu.pl/kontroler.php?_action=katalog2/osoby/pracownicyJednostki&jed_org_kod=A000000',
            'description': 'USOS server - employees'
        },
    ],

############################## GROUPS URL's ##############################

    'ioe_groups': [
        {
            'url_lato': 'https://ioe.wat.edu.pl/plany/lato/index.xml',
            'description': 'IOE groups'
        }
    ],

    'wcy_groups': [
        {
            'url': 'https://planzajec.wcy.wat.edu.pl/rozklad',
            'description': 'WCY groups'
        }
    ],

    'wel_groups': [
        {
            'url_lato': 'https://plany.wel.wat.edu.pl/lato/index.xml',
            'description': 'WEL groups'
        }
    ],
    
    # 'wig_groups': [
    #     {
    #         'url': '',
    #         'description': 'WIG groups'
    #     }
    # ],
    
    'wim_groups': [
        {
            'url_lato': 'https://www.wim.wat.edu.pl/wp-content/uploads/rozklady/lato/index.xml',
            'description': 'WIM groups'
        }
    ],

    'wlo_groups': [
        {
            'url_lato': 'https://wlo.wat.edu.pl/planzajec/letni/index.xml',
            'description': 'WLO groups'
        }
    ],

    # 'wml_groups': [
    #     {
    #         'url': 'https://wml.wat.edu.pl/rozklady-zajec/',
    #         'description': 'WML groups'
    #     }
    # ],

    'wtc_groups': [
        {
            'url': 'https://www.wtc.wat.edu.pl/Plany/index.xml',
            'description': 'WTC groups'
        }
    ],

############################## SCHEDULES URL's ##############################

    'ioe_schedule': [
        {
            'url_lato': 'https://ioe.wat.edu.pl/plany/lato/{group}.htm',
            'description': 'IOE {group} schedule'
        }
    ],

    'wcy_schedule': [
        {
            'url': 'https://planzajec.wcy.wat.edu.pl/pl/rozklad?grupa_id={group}',
            'description': 'WCY {group} schedule'
        }
    ],

    'wel_schedule': [
        {
            'url_lato': 'https://plany.wel.wat.edu.pl/lato/{group}.htm',
            'description': 'WEL {group} schedule'
        }
    ],
    
    # 'wig_schedule': [
    #     {
    #         'url': '',
    #         'description': 'WIG {group} schedule'
    #     }
    # ],
    
    'wim_schedule': [
        {
            'url_lato': 'https://www.wim.wat.edu.pl/wp-content/uploads/rozklady/lato/{group}.htm',
            'description': 'WIM {group} schedule'
        }
    ],

    'wlo_schedule': [
        {
            'url_lato': 'https://wlo.wat.edu.pl/planzajec/letni/{group}.htm',
            'description': 'WLO {group} schedule'
        }
    ],
    
    # 'wml_schedule': [
    #     {
    #         'url': 'https://wml.wat.edu.pl/rozklady-zajec/',
    #         'description': 'WML {group} schedule'
    #     }
    # ],
    
    'wtc_schedule': [
        {
            'url': 'https://www.wtc.wat.edu.pl/Plany/{group}.htm',
            'description': 'WTC {group} schedule'
        }
    ]
}

############################ calendar scrapers definitions ############################

BLOCK_TIMES = {
    "block1": ("08:00", "09:35"),
    "block2": ("09:50", "11:25"),
    "block3": ("11:40", "13:15"),
    "block4": ("13:30", "15:05"),
    "block5": ("16:00", "17:35"),
    "block6": ("17:50", "19:25"),
    "block7": ("19:40", "21:15"),
    '1-2': ("08:00", "09:35"),
    '3-4': ("09:50", "11:25"),
    '5-6': ("11:40", "13:15"),
    '7-8': ("13:30", "15:05"),
    '9-10': ("16:00", "17:35"),
    '11-12': ("17:50", "19:25"),
    '13-14': ("19:40", "21:15")
}

ROMAN_MONTH = {
    'I': 1,
    'II': 2,
    'III': 3,
    'IV': 4,
    'V': 5,
    'VI': 6,
    'VII': 7,
    'VIII': 8,
    'IX': 9,
    'X': 10,
    'XI': 11,
    'XII': 12
}

DATE_TOKEN_RE = re.compile(r'^(\d{2})\s+([IVX]{1,4})$')

TYPE_FULL_MAP = {
    "(w)": "Wykład",
    "(L)": "Laboratorium",
    "(ć)": "Ćwiczenia",
    "(P)": "Projekt",
    "(S)": "Seminarium",
    "(E)": "Egzamin",
    "(Ep)": "Egzamin poprawkowy",
    "(inne)": "inne",
}

TYPE_SYMBOLS = set(TYPE_FULL_MAP.keys())

def sanitize_filename(filename):
    return re.sub(r'[<>:"\\|?*]', "_", filename)