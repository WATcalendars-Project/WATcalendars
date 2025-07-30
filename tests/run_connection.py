# run_connection.py
import sys
import os

# Dodaj ścieżkę do src/watcalendars do PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'watcalendars'))

from connection import load_url_from_config  # type: ignore

if len(sys.argv) < 2:
    print("Użycie: python run_connection.py <category> [faculty] [url_type] [--test]")
    print("Przykłady:")
    print("  python run_connection.py usos")
    print("  python run_connection.py groups ioe url_lato --test")
    sys.exit(1)

# Sprawdź czy jest flaga --test
test_connection = '--test' in sys.argv
if test_connection:
    sys.argv.remove('--test')  # usuń flagę z argumentów

category = sys.argv[1]
faculty = sys.argv[2] if len(sys.argv) > 2 else None
url_type = sys.argv[3] if len(sys.argv) > 3 else 'url'

url, description = load_url_from_config(category, faculty, url_type)

# Jeśli jest flaga --test, uruchom test połączenia
if test_connection and url:
    from connection import test_connection_with_monitoring  # type: ignore
    test_connection_with_monitoring(url, description)
elif test_connection and not url:
    print("❌ Nie można przetestować - brak URL!")