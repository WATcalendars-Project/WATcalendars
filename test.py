import sys
import os

def test_setup():
    print("--- WATcalendars: Test Środowiska ---")
    
    print(f"[OK] Python version: {sys.version.split()[0]}")
    
    folders = ['db', 'src/watcalendars']
    for f in folders:
        if os.path.exists(f):
            print(f"[OK] Folder '{f}' istnieje.")
        else:
            print(f"[!!] Brak folderu '{f}' - upewnij się, że jesteś w głównym katalogu projektu.")

    try:
        import requests
        print("[OK] Biblioteka 'requests' gotowa.")
    except ImportError:
        print("[!!] Brak biblioteki 'requests'. Uruchom: pip install -r requirements.txt")

    try:
        import playwright
        print("[OK] Biblioteka 'playwright' gotowa.")
    except ImportError:
        print("[!!] Brak biblioteki 'playwright'. Uruchom: pip install -r requirements.txt")

    print("--- Test zakończony pomyślnie! ---")

if __name__ == "__main__":
    test_setup()