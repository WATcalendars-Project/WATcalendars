class LogColors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    OKCYAN = '\033[96m'
    ENDC = '\033[0m'
    CONNECT = '\033[95m'

# Predefiniowane pokolorowane tagi
OK = f"{LogColors.OKGREEN}[OK]{LogColors.ENDC}"
ERROR = f"{LogColors.FAIL}[ERROR]{LogColors.ENDC}"
WARNING = f"{LogColors.WARNING}[WARNING]{LogColors.ENDC}"
INFO = f"{LogColors.OKCYAN}[INFO]{LogColors.ENDC}"
GET = f"{LogColors.CONNECT}[GET]{LogColors.ENDC}"
RESPONSE = f"{LogColors.CONNECT}[RESPONSE]{LogColors.ENDC}"
SUCCESS = f"{LogColors.OKGREEN}[SUCCESS]{LogColors.ENDC}"
CHANGED = f"{LogColors.WARNING}changed{LogColors.ENDC}"
UNCHANGED = f"{LogColors.OKGREEN}unchanged{LogColors.ENDC}"
ADDED = f"{LogColors.WARNING}added{LogColors.ENDC}"
