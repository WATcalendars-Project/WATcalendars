import os

# Main directory for WATcalendars (src/watcalendars)
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory for storing database files
DB_DIR = os.path.abspath(os.path.join(PACKAGE_DIR, "..", "..", "db"))
GROUPS_DIR = os.path.join(DB_DIR, "groups")