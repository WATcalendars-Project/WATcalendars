import sys
import time
import os
import threading
import asyncio
from time import perf_counter

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

RESET = '\033[0m'

GET = f"{MAGENTA}→{RESET}"
RESPONSE = f"{BRIGHT_BLUE}←{RESET}"
ERROR = f"{RED}E{RESET}:"
WARNING = f"{BRIGHT_YELLOW}W{RESET}:"
INFO = f"[{BRIGHT_BLUE}INFO{RESET}]:"
OK = f"{GREEN}OK{RESET}:"


# Function to entry log message at the top of "log" or just add message log nad blank line under
# Use:
# logs = []
# log_entry(f"{OK} Task finished.", logs)
def log_entry(message, logs_list=None):
    if logs_list is not None:
        logs_list.append(message)
    print(f"\r{' ' * 80}\r{message}")


# Function to run a task with a spinner
# Use:
# def my_task():
#   ...your task...
# log("Checking dependencies... ", my_task)
def log(task_name, task_fn, progress_info=None):
    spin_chars = ['|', '/', '-', '\\']
    result = {"done": False, "return_value": None, "exception": None}

    def wrapper():
        try:
            result["return_value"] = task_fn()
        except Exception as e:
            result["exception"] = e
        finally:
            result["done"] = True

    t = threading.Thread(target=wrapper)
    t.start()
    i = 0
    max_line_length = 0

    try:
        terminal_width = os.get_terminal_size().columns
    except:
        terminal_width = 80  
    
    while not result["done"]:
        spinner_char = spin_chars[i % len(spin_chars)]
        left_part = f"{task_name} {spinner_char}"
        
        if progress_info:
            available_space = terminal_width - len(left_part) - len(progress_info) - 1
            if available_space > 0:
                current_line = f"{left_part}{' ' * available_space}{progress_info}"
            else:
                current_line = f"{left_part} {progress_info}"
        else:
            current_line = left_part
            
        max_line_length = max(max_line_length, len(current_line))
        sys.stdout.write(f"\r{' ' * max_line_length}\r{current_line}")
        sys.stdout.flush()
        time.sleep(0.2)
        i += 1

    t.join()

    if progress_info:
        final_line = f"{task_name} Done.{' ' * (terminal_width - len(task_name) - len('Done') - len(progress_info) - 1)}{progress_info}"
    else:
        final_line = f"{task_name} Done."

    sys.stdout.write(f"\r{' ' * max_line_length}\r{final_line}\n")
    sys.stdout.flush()
    
    if result["exception"]:
        raise result["exception"]
    
    return result["return_value"]


# Function to run a task with a spinner with async mode
# Use:
# stop_event, spinner_task = start_spinner("Scraping groups", len(pairs), lambda: done, interval=0.2)
# stop_event.set()
# await spinner_task
async def _spinner_loop(label: str, total: int, get_done, stop_event: asyncio.Event, interval: float = 0.2, frames=None):
    frames = ["-", "\\", "|", "/"]
    i = 0
    next_tick = perf_counter()

    try:
        while not stop_event.is_set():

            try:
                done = int(get_done())

            except Exception:
                done = 0

            done = max(0, min(done, total))
            sys.stderr.write("\r\033[2K" + f"{label} ({done}/{total})... {frames[i % len(frames)]}")
            sys.stderr.flush()
            i += 1
            next_tick += interval
            await asyncio.sleep(interval)

        try:
            done = int(get_done())

        except Exception:
            done = total

        done = max(0, min(done, total))
        sys.stderr.write("\r\033[2K" + f"{label} ({done}/{total})... done\n")
        sys.stderr.flush()

    finally:
        sys.stderr.write("\033[?25h")
        sys.stderr.flush()

def start_spinner(label: str, total: int, get_done, interval: float = 0.2, frames=None):
    stop_event = asyncio.Event()
    task = asyncio.create_task(_spinner_loop(label, total, get_done, stop_event, interval, frames))
    return stop_event, task


# Function to run a task with a spinner and progress
# Usage:
# def progress():
#     return f"({groups_done}/{total_groups})"
# def my_task():
#   ...your_task...
# log_parsing("Parsing events for WCY schedules", my_task, progress_fn=progress)
def log_parsing(task_name, task_fn, progress_fn, interval: float = 0.2, frames = None):
    frames = frames or ["-", "\\", "|", "/"]
    result = {"done": False, "return_value": None, "exception": None}

    def wrapper():
        try:
            result["return_value"] = task_fn()
        except Exception as e:
            result["exception"] = e
        finally:
            result["done"] = True

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    i = 0

    def _progress_text():
        try:
            return "" if progress_fn is None else (str(progress_fn()) or "")
        except Exception:
            return ""

    try:
        while not result["done"]:
            spinner_char = frames[i % len(frames)]
            prog = _progress_text()
            if prog:
                line = f"{task_name} {prog}... {spinner_char}"
            else:
                line = f"{task_name}... {spinner_char}"
            sys.stdout.write("\r\033[2K" + line)
            sys.stdout.flush()
            time.sleep(interval)
            i += 1
    finally:
        t.join()
        prog = _progress_text()
        if prog:
            line = f"{task_name} {prog}... Done."
        else:
            line = f"{task_name}... Done."
        sys.stdout.write("\r\033[2K" + line + "\n")
        sys.stdout.flush()
    if result["exception"]:
        raise result["exception"]
    return result["return_value"]