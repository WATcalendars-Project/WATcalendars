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

# Reset codes
RESET = '\033[0m'
RESET_BOLD = '\033[21m'
RESET_DIM = '\033[22m'
RESET_ITALIC = '\033[23m'
RESET_UNDERLINE = '\033[24m'
RESET_BLINK = '\033[25m'
RESET_REVERSE = '\033[27m'
RESET_STRIKETHROUGH = '\033[29m'

# Defined logs
GET = f"{BRIGHT_BLUE}→{RESET}"
RESPONSE = f"{BRIGHT_BLUE}←{RESET}"
ERROR = f"{RED}E{RESET}:"
WARNING = f"{BRIGHT_YELLOW}W{RESET}:"
INFO = f"[{BRIGHT_BLUE}INFO{RESET}]:"
OK = f"{GREEN}OK{RESET}:"


# Helper function to log message and print it with clearing line

# Args:
#     message (str): Message to log and print
#     logs_list (list, optional): List to append log entry to
def log_entry(message, logs_list=None):
    if logs_list is not None:
        logs_list.append(message)
    print(f"\r{' ' * 80}\r{message}")

# Function to run a task with a spinner
# Use:
# def my_task():
#     # ...your task...
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
    # Starting spinner as asyncio.Task.
    # Returns (stop_event, task). Set stop_event.set() and await task to finish.
    # get_done: callable without arguments returning current counter (int).
    stop_event = asyncio.Event()
    task = asyncio.create_task(_spinner_loop(label, total, get_done, stop_event, interval, frames))
    return stop_event, task