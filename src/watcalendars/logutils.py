#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import os
import threading

# Define ANSI color codes for terminal output
# These can be used to colorize log messages in the terminal.
# usage:
# print(f"{RED}red color{RESET}")

# Basic colors (30-37)
BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'

# Bright colors (90-97)
BRIGHT_BLACK = '\033[90m'
BRIGHT_RED = '\033[91m'
BRIGHT_GREEN = '\033[92m'
BRIGHT_YELLOW = '\033[93m'
BRIGHT_BLUE = '\033[94m'
BRIGHT_MAGENTA = '\033[95m'
BRIGHT_CYAN = '\033[96m'
BRIGHT_WHITE = '\033[97m'

# Background colors (40-47)
BG_BLACK = '\033[40m'
BG_RED = '\033[41m'
BG_GREEN = '\033[42m'
BG_YELLOW = '\033[43m'
BG_BLUE = '\033[44m'
BG_MAGENTA = '\033[45m'
BG_CYAN = '\033[46m'
BG_WHITE = '\033[47m'

# Bright background colors (100-107)
BG_BRIGHT_BLACK = '\033[100m'
BG_BRIGHT_RED = '\033[101m'
BG_BRIGHT_GREEN = '\033[102m'
BG_BRIGHT_YELLOW = '\033[103m'
BG_BRIGHT_BLUE = '\033[104m'
BG_BRIGHT_MAGENTA = '\033[105m'
BG_BRIGHT_CYAN = '\033[106m'
BG_BRIGHT_WHITE = '\033[107m'

# Text styles
BOLD = '\033[1m'
DIM = '\033[2m'
ITALIC = '\033[3m'
UNDERLINE = '\033[4m'
BLINK = '\033[5m'
REVERSE = '\033[7m'
STRIKETHROUGH = '\033[9m'

# Reset codes
RESET = '\033[0m'
RESET_BOLD = '\033[21m'
RESET_DIM = '\033[22m'
RESET_ITALIC = '\033[23m'
RESET_UNDERLINE = '\033[24m'
RESET_BLINK = '\033[25m'
RESET_REVERSE = '\033[27m'
RESET_STRIKETHROUGH = '\033[29m'

# Zdefiniowane logi
GET = f"{BRIGHT_BLUE}→{RESET}"
RESPONSE = f"{BRIGHT_BLUE}←{RESET}"
ERROR = f"{RED}E{RESET}:"
WARNING = f"{YELLOW}W{RESET}:"
INFO = f"[{BRIGHT_BLUE}INFO{RESET}]:"
OK = f"{GREEN}OK{RESET}:"



# Function to run a task with a spinner
# Use:
# def my_task():
#     # ...your task...
# log("Checking dependencies... ", my_task)
def log(task_name, task_fn, progress_info=None):
    spin_chars = ['|', '/', '-', '\\']
    # Initialize a result dictionary to store the task's return value and any exception raised
    result = {"done": False, "return_value": None, "exception": None}

    # Define a wrapper function to run the task and handle exceptions
    def wrapper():
        try:
            result["return_value"] = task_fn()
        except Exception as e:
            result["exception"] = e
        finally:
            result["done"] = True

    # Start the wrapper function in a separate thread
    t = threading.Thread(target=wrapper)
    t.start()

    i = 0
    max_line_length = 0

    # Try to get the terminal width for formatting the spinner output
    try:
        terminal_width = os.get_terminal_size().columns
    except:
        terminal_width = 80  
    
    # Loop until the task is done
    while not result["done"]:
        # Get the current spinner character based on the iteration index
        spinner_char = spin_chars[i % len(spin_chars)]
        # Format the left part of the spinner output
        left_part = f"{task_name} {spinner_char}"
        
        # If progress_info is provided, format it and calculate available space
        if progress_info:
            # Calculate the available space for the spinner output
            available_space = terminal_width - len(left_part) - len(progress_info) - 1
            # If available space is positive, fill it with spaces
            if available_space > 0:
                current_line = f"{left_part}{' ' * available_space}{progress_info}"
            # Otherwise, just append the progress_info directly
            else:
                current_line = f"{left_part} {progress_info}"
        else:
            current_line = left_part
            
        # Print the current line to the terminal
        max_line_length = max(max_line_length, len(current_line))
        sys.stdout.write(f"\r{' ' * max_line_length}\r{current_line}")
        sys.stdout.flush()
        time.sleep(0.2)
        i += 1

    # Wait for the task thread to finish
    t.join()
    # If progress_info is provided, format the final output
    if progress_info:
        final_line = f"{task_name} Done.{' ' * (terminal_width - len(task_name) - len('Done') - len(progress_info) - 1)}{progress_info}"
    # If progress_info is not provided, just indicate the task is done
    else:
        final_line = f"{task_name} Done."

    # Clear the current line and print the final output
    # This ensures the final output is displayed correctly in the terminal
    sys.stdout.write(f"\r{' ' * max_line_length}\r{final_line}\n")
    sys.stdout.flush()
    
    if result["exception"]:
        raise result["exception"]
    
    return result["return_value"]