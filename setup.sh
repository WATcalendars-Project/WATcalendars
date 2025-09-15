#!/bin/bash

echo -e ""
echo -e "\033[1;32m         █     █░ ▄▄▄     ▄▄▄█████▓      \033[0;0mWelcome to the \033[0;32mWATcalendars\033[0m project!"
echo -e "\033[1;32m        ▓█░ █ ░█░▒████▄   ▓  ██▒ ▓▒      \033[0mversion: 0.2.0"
echo -e "\033[1;32m        ▒█░ █ ░█ ▒██  ▀█▄ ▒ ▓██░ ▒░      \033[0;0m------------------------"
echo -e "\033[1;32m        ░█░ █ ░█ ░██▄▄▄▄██░ ▓██▓ ░       \033[1;32mThis \033[0;32mopen-source\033[0m project,"
echo -e "\033[1;32m       ░░██▒██▓  ▓█   ▓██▒ ▒██▒ ░        \033[0mallows you to \033[1mlearn\033[0m and \033[1mmanage\033[0m"
echo -e "\033[1;32m       ░ ▓░▒ ▒   ▒▒   ▓▒█░ ▒ ░░          \033[0mscraping scripts."
echo -e "\033[1;32m         ▒ ░ ░    ▒   ▒▒ ░   ░           \033[0;32mReady-to-use \033[1;32mcalendars\033[0m for your phone\033[0m"
echo -e "\033[1;32m         ░   ░    ░   ▒    ░             \033[0mcan be set from:"
echo -e "\033[1;32m  ░█▀▀░█▀█░█░░░█▀▀░█▀█░█▀▄░█▀█░█▀▄░█▀▀   \033[0m\033[1;4m[]\033[0m"
echo -e "\033[1;32m  ░█░░░█▀█░█░░░█▀▀░█░█░█░█░█▀█░█▀▄░▀▀█   "
echo -e "\033[1;32m  ░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀▀░░▀░▀░▀░▀░▀▀▀   \033[0m------------------------"
echo -e "\033[1;32m                                         \033[0mby \033[1;34mDominik Serafin\033[0m"
echo -e "                                         \033[0m\033[1;4m[]\033[0m"
echo -e ""
echo -e ""

# Function to ask user for permission
ask_permission() {
    local message="$1"
    read -r -p "$message [Y/n] " choice
    case "$choice" in
        [Nn]* ) return 1;;
        * ) return 0;;
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status messages
print_info() { echo -e "[INFO]: $1"; }
print_ok() { echo -e "\033[0;32mOK\033[0m: $1"; }
print_error() { echo -e "\033[0;31mERROR\033[0m: $1"; }

# Main setup
echo -e "This script will install Python dependencies required for WATcalendars project."
echo -e "Required: python3, pip3, python3-venv, beautifulsoup4, playwright"
echo -e ""

if ! ask_permission "Do you want to continue?"; then
    echo -e "Setup cancelled."
    exit 0
fi

# Function to detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo $ID
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

# Function to install system packages based on distribution
install_system_package() {
    local package="$1"
    local distro=$(detect_distro)
    
    case "$distro" in
        ubuntu|debian|pop|mint)
            sudo apt-get update && sudo apt-get install -y "$package"
            ;;
        fedora)
            sudo dnf install -y "$package"
            ;;
        centos|rhel|rocky|alma)
            sudo yum install -y "$package"
            ;;
        arch|manjaro|endeavour)
            sudo pacman -S --noconfirm "$package"
            ;;
        opensuse*)
            sudo zypper install -y "$package"
            ;;
        alpine)
            sudo apk add "$package"
            ;;
        *)
            print_error "Unsupported Linux distribution: $distro"
            echo -e "Please install $package manually and run this script again."
            exit 1
            ;;
    esac
}

# Function to get package names for different distributions
get_package_name() {
    local generic_name="$1"
    local distro=$(detect_distro)
    
    case "$generic_name" in
        python3)
            case "$distro" in
                ubuntu|debian|pop|mint) echo "python3" ;;
                fedora|centos|rhel|rocky|alma) echo "python3" ;;
                arch|manjaro|endeavour) echo "python" ;;
                opensuse*) echo "python3" ;;
                alpine) echo "python3" ;;
                *) echo "python3" ;;
            esac
            ;;
        python3-pip)
            case "$distro" in
                ubuntu|debian|pop|mint) echo "python3-pip" ;;
                fedora) echo "python3-pip" ;;
                centos|rhel|rocky|alma) echo "python3-pip" ;;
                arch|manjaro|endeavour) echo "python-pip" ;;
                opensuse*) echo "python3-pip" ;;
                alpine) echo "py3-pip" ;;
                *) echo "python3-pip" ;;
            esac
            ;;
        python3-venv)
            case "$distro" in
                ubuntu|debian|pop|mint) echo "python3-venv" ;;
                fedora|centos|rhel|rocky|alma) echo "python3-venv" ;;
                arch|manjaro|endeavour) echo "" ;; # Built into python package
                opensuse*) echo "python3-venv" ;;
                alpine) echo "py3-virtualenv" ;;
                *) echo "python3-venv" ;;
            esac
            ;;
    esac
}

echo -e ""
echo -e "=== Detecting System Information ==="
DISTRO=$(detect_distro)
print_info "Detected Linux distribution: $DISTRO"

echo -e ""
echo -e "=== Checking System Dependencies ==="

# Check Python 3
if ! command_exists python3; then
    print_info "Python3 not found"
    if ask_permission "Install python3?"; then
        PYTHON_PKG=$(get_package_name "python3")
        if install_system_package "$PYTHON_PKG"; then
            print_ok "Python3 installed successfully"
        else
            print_error "Failed to install python3"
            exit 1
        fi
    else
        print_error "Python3 is required"
        exit 1
    fi
else
    print_ok "Python3 found: $(python3 --version)"
fi

# Check pip3
if ! command_exists pip3; then
    print_info "pip3 not found"
    if ask_permission "Install python3-pip?"; then
        PIP_PKG=$(get_package_name "python3-pip")
        if install_system_package "$PIP_PKG"; then
            print_ok "pip3 installed successfully"
        else
            print_error "Failed to install pip3"
            exit 1
        fi
    else
        print_error "pip3 is required"
        exit 1
    fi
else
    print_ok "pip3 found: $(pip3 --version)"
fi

# Check python3-venv
if ! python3 -c "import venv" 2>/dev/null; then
    VENV_PKG=$(get_package_name "python3-venv")
    if [ -n "$VENV_PKG" ]; then
        print_info "python3-venv not found"
        if ask_permission "Install python3-venv?"; then
            if install_system_package "$VENV_PKG"; then
                print_ok "python3-venv installed successfully"
            else
                print_error "Failed to install python3-venv"
                exit 1
            fi
        else
            print_error "python3-venv is required"
            exit 1
        fi
    else
        print_info "python3-venv is built into Python on this distribution"
    fi
else
    print_ok "python3-venv found"
fi

echo -e ""
echo -e "=== Setting Up Virtual Environment ==="

# Create virtual environment
if [ ! -d ".venv" ]; then
    print_info "Creating virtual environment..."
    if python3 -m venv .venv; then
        print_ok "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
else
    print_ok "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate

if [ -z "$VIRTUAL_ENV" ]; then
    print_error "Failed to activate virtual environment"
    exit 1
else
    print_ok "Virtual environment activated"
fi

echo -e ""
echo -e "=== Installing Python Dependencies ==="

# Upgrade pip
print_info "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1

# Install project with dependencies from pyproject.toml
print_info "Installing project dependencies (beautifulsoup4, playwright)..."
if pip install -e .; then
    print_ok "Python dependencies installed successfully"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

echo -e ""
echo -e "=== Installing Playwright Browsers ==="

# Install Playwright browsers
if pip show playwright >/dev/null 2>&1; then
    if [ ! -f ".venv/.playwright_installed" ]; then
        print_info "Installing Playwright browser binaries..."
        if ask_permission "Install Playwright browsers? (required for web scraping)"; then
            if playwright install; then
                print_ok "Playwright browsers installed successfully"
                touch .venv/.playwright_installed
            else
                print_error "Failed to install Playwright browsers"
                exit 1
            fi
        else
            print_info "Playwright browsers not installed - web scraping may not work"
        fi
    else
        print_ok "Playwright browsers already installed"
    fi
else
    print_error "Playwright package not found"
    exit 1
fi

echo -e ""
echo -e "=== Setup Complete ==="
print_ok "All dependencies installed successfully!"
echo -e ""
echo -e "You can now run the project modules:"
echo -e "  • Employee scraper: \033[1;32mpython3 -m watcalendars.watemployees\033[0m"
echo -e "  • Group scrapers: \033[1;32mpython3 -m watcalendars.groups.groups_wcy\033[0m"
echo -e "  • Calendar scrapers: \033[1;32mpython3 -m watcalendars.calendar_wcy\033[0m"
echo -e ""
echo -e "Remember to activate virtual environment before running:"
echo -e "  \033[1;33msource .venv/bin/activate\033[0m"
echo -e ""
echo -e "For more information check file \"help.txt\" in the repository or type:"
echo -e "  \033[1;33mcat help.txt\033[0m"
echo -e ""