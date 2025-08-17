# employees data loader for WATcalendars
# This module handles loading employee data for calendars from file employees.txt
# Usage:
# employees = load_employees()

import os
from watcalendars.utils.logutils import ERROR as E
from watcalendars import DB_DIR

def load_employees():
    employees_file = os.path.join(DB_DIR, "employees.txt")
    employees = {}

    if os.path.exists(employees_file):

        with open(employees_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"): continue
                parts = line.split("\t")

                if len(parts) == 2:
                    degree = parts[0].strip()
                    full_name = parts[1].replace(" [NEW]", "").strip()
                    employees[full_name] = f"{degree} {full_name}".strip()
                    
    return employees