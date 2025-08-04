# run_connection.py
import sys
import os

# Add the src directory to the Python path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'watcalendars'))

from url_loader import load_url_from_config  # type: ignore

# Function to display help information
def show_help():
    print("run_connection.py - Test URL connections from configuration")
    print()
    print("Usage: python run_connection.py <category> [faculty] [url_type] [--test] [--help]")
    print()
    print("Arguments:")
    print("  category    Required. Category of URLs to load (e.g., 'usos', 'groups')")
    print("  faculty     Optional. Faculty code (e.g., 'ioe', 'wcy', 'wel', 'wig', 'wim', 'wlo', 'wml', 'wtc')")
    print("  url_type    Optional. Type of URL to load (default: 'url')")
    print()
    print("Options:")
    print("  --test      Test the connection to the loaded URL")
    print("  --help      Show this help message and exit")
    print()
    print("Examples:")
    print("  python run_connection.py usos")
    print("  python run_connection.py groups ioe")
    print("  python run_connection.py groups ioe url_lato --test")
    print("  python run_connection.py --help")

# Check for help flag first
if '--help' in sys.argv or '-h' in sys.argv:
    show_help()
    sys.exit(0)

if len(sys.argv) < 2:
    print("Usage: python run_connection.py <category> [faculty] [url_type] [--test] [--help]")
    print("Use --help for more detailed information.")
    sys.exit(1)

# Check if the --test flag is present
test_connection = '--test' in sys.argv
if test_connection:
    sys.argv.remove('--test')  # remove the flag from the arguments

category = sys.argv[1]
faculty = sys.argv[2] if len(sys.argv) > 2 else None
url_type = sys.argv[3] if len(sys.argv) > 3 else 'url'

url, description = load_url_from_config(category, faculty, url_type)

# If the test_connection flag is set and a URL is found, run the connection test
if test_connection and url:
    from connection import test_connection_with_monitoring  # type: ignore
    test_connection_with_monitoring(url, description)
elif test_connection and not url:
    print("Cannot test connection: URL not found.")