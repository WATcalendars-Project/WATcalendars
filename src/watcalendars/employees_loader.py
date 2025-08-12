# employees data loader for WATcalendars
# This module handles loading employee data from file employees.txt
import os

from logutils import ERROR as E

# Directory for storing database files
script_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.join(script_dir, "..", "..", "db")

# Function to load employee data from a file
def load_employees():
    employees_file = os.path.join(db_dir, "employees.txt")
    employees = {}
    if os.path.exists(employees_file):
        with open(employees_file, "r", encoding="utf-8") as f:
            # Read each line, split by tab, and store in a dictionary
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split("\t")
                # Check if the line has exactly two parts: degree and full name
                if len(parts) == 2:
                    # Normalize degree and full name
                    degree = parts[0].strip()
                    # Remove [NEW] marker if present
                    full_name = parts[1].replace(" [NEW]", "").strip()
                    # Store in the dictionary
                    employees[full_name] = f"{degree} {full_name}".strip()
    return employees