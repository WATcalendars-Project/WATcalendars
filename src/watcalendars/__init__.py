import os

PACKAGE_DIR = os.path.dirname(__file__)

PROJECT_ROOT = os.path.abspath(os.path.join(PACKAGE_DIR, "..", ".."))

DB_DIR = os.path.join(PROJECT_ROOT, "db")

GROUPS_DIR = os.path.join(DB_DIR, "groups_url")
GROUPS_CONFIG = os.path.join(DB_DIR, 'url_for_group.json')
SCHEDULES_CONFIG = os.path.join(DB_DIR, 'url_for_schedules.json')
CALENDARS_DIR = os.path.join(DB_DIR, "calendars")
SCHEDULES_DIR = os.path.join(DB_DIR, "schedules")