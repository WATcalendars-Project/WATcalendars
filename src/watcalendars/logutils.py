# Definicja kolorow do printa
# uzycie:
# print(f"{RED}kolor czerwony{RESET}")
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Zdefiniowane logi
E = f"{RED}E{RESET}:"
W = f"{YELLOW}W{RESET}:"
INFO = f"[{BLUE}INFO{RESET}]:"
OK = f"{GREEN}OK{RESET}:"

import threading
import time
import sys
import os

class Spinner:
    def __init__(self, message="Loading"):
        self.message = message
        self.spinner_chars = "|/-\\"
        self.running = False
        self.thread = None
        
    def _spin(self):
        i = 0
        while self.running:
            char = self.spinner_chars[i % len(self.spinner_chars)]
            
            # Print spinner without newline, overwrite same position
            sys.stdout.write(f"{char}\b")
            sys.stdout.flush()
            
            time.sleep(0.1)
            i += 1
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        # Clear spinner with space and backspace
        sys.stdout.write(" \b")
        sys.stdout.flush()

class SpinnerContext:
    def __init__(self, message="Loading"):
        self.spinner = Spinner(message)
    
    def __enter__(self):
        self.spinner.start()
        return self.spinner
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.spinner.stop()