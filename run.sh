#!/bin/bash

echo -e ""
echo -e "\033[1;32m         █     █░ ▄▄▄     ▄▄▄█████▓      \033[0;0mHello \033[1;31m$USER\033[1;0m@\033[1;31m$HOSTNAME\033[0m,"
echo -e "\033[1;32m        ▓█░ █ ░█░▒████▄   ▓  ██▒ ▓▒      \033[0;0mwelcome to the \033[0;32mWATcalendars\033[0m project!"
echo -e "\033[1;32m        ▒█░ █ ░█ ▒██  ▀█▄ ▒ ▓██░ ▒░      \033[0;0m------------------------"
echo -e "\033[1;32m        ░█░ █ ░█ ░██▄▄▄▄██░ ▓██▓ ░       \033[1;32mThis \033[0;32mopen-source\033[0m project,"
echo -e "\033[1;32m       ░░██▒██▓  ▓█   ▓██▒ ▒██▒ ░        \033[0mallows you to \033[1mlearn\033[0m and \033[1mmanage\033[0m"
echo -e "\033[1;32m       ░ ▓░▒ ▒   ▒▒   ▓▒█░ ▒ ░░          \033[0mscraping scripts."
echo -e "\033[1;32m         ▒ ░ ░    ▒   ▒▒ ░   ░           \033[0;32mReady-to-use \033[1;32mcalendars\033[0m for your phone\033[0m"
echo -e "\033[1;32m         ░   ░    ░   ▒    ░             \033[0mcan be set from:"
echo -e "\033[1;32m  ░█▀▀░█▀█░█░░░█▀▀░█▀█░█▀▄░█▀█░█▀▄░█▀▀   \033[0m\033[1;4m[https://kalendarze.bieda.it]\033[0m"
echo -e "\033[1;32m  ░█░░░█▀█░█░░░█▀▀░█░█░█░█░█▀█░█▀▄░▀▀█   "
echo -e "\033[1;32m  ░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀▀░░▀░▀░▀░▀░▀▀▀   \033[0m------------------------"
echo -e "\033[1;32m                                         \033[0mby \033[1;34mDominik Serafin\033[0m"
echo -e "                                         \033[0m\033[1;4m[https://serafin.byst.re]\033[0m"
echo -e ""
echo -e ""
echo -e "You are going to check required dependencies and install missing ones to run this project."
echo -e "[INFO]: required (pip3, python3-venv, python3 and python modules)"
read -r -p "Do you want to continue? [Y/n] " start_choice

if [[ "$start_choice" =~ ^[Nn]$ ]]; then
    echo -e "Exiting..."
    exit 0
elif [[ "$start_choice" =~ ^[Yy]$ ]]; then
    echo -e "Checking system dependencies..."
else
    echo -e "Invalid choice. Exiting..."
    exit 1
fi

declare -A system_dependencies
system_dependencies[python3_packages]="python3"
system_dependencies[pip3_packages]="python3-pip"
system_dependencies[venv_packages]="python3-venv"

missing_system_dependencies=()

# Check python3
if ! command -v "python3" > /dev/null 2>&1; then
    echo -e "[INFO]: missing python3"
    missing_system_dependencies+=("${system_dependencies[python3_packages]}")
else
    echo -e "[INFO]: found python3"
fi

# Check pip3
if ! command -v "pip3" > /dev/null 2>&1; then
    echo -e "[INFO]: missing pip3"
    missing_system_dependencies+=("${system_dependencies[pip3_packages]}")
else
    echo -e "[INFO]: found pip3"
fi

# Check python3-venv
if python3 -c "import venv" 2>/dev/null; then
    echo -e "[INFO]: found python3-venv"
else
    echo -e "[INFO]: missing python3-venv"
    missing_system_dependencies+=("${system_dependencies[venv_packages]}")
fi

# Install missing system dependencies
if [ ${#missing_system_dependencies[@]} -gt 0 ]; then
    echo -e "Installing missing system dependencies..."
    for dep in "${missing_system_dependencies[@]}"; do
        if ! sudo apt-get install "$dep" -y ; then
            echo -e "\033[0;31mE\033[0m: Failed to install $dep"
            exit 1
        else
            echo -e "\033[0;32mOK\033[0m: Successfully installed $dep"
        fi
    done
fi

# Checking or creating virtual environment
if [ ! -d "venv" ]; then
    echo -e "[INFO]: Virtual environment not found." 
    echo -e "Creating python virtual environment in WATcalendars/venv..."
    python3 -m venv .venv
    if [ ! -d ".venv" ]; then
        echo -e "\033[0;31mE\033[0m: Failed to create virtual environment"
        exit 1
    fi
    echo -e "Activating virtual environment..."
    source .venv/bin/activate
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "\033[0;31mE\033[0m: Failed to activate virtual environment"
        exit 1
    else
        echo -e "\033[0;32mOK\033[0m: Virtual environment activated successfully"
    fi
else
    echo -e "[INFO]: Virtual environment found."
    if [ ! -f ".venv/bin/activate" ]; then
        echo -e "[INFO]: Virtual environment is broken or not created."
        echo -e "Trying to reinstall python3-venv..."
        sudo apt-get install --reinstall python3-venv
        rm -rf .venv
        echo -e "Recreating virtual environment..."
        python3 -m venv .venv
        if [ ! -f ".venv/bin/activate" ]; then
            echo -e "\033[0;31mE\033[0m: Failed to create virtual environment"
            exit 1
        fi
        echo -e "Activating virtual environment..."
        source .venv/bin/activate
        if [ -z "$VIRTUAL_ENV" ]; then
            echo -e "\033[0;31mE\033[0m: Failed to activate virtual environment"
            exit 1
        fi
    else
        echo -e "\033[0;32mOK\033[0m: Virtual environment is available"
    fi
fi

# Activate virtual environment for package installation
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "Activating virtual environment..."
    source .venv/bin/activate
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "\033[0;31mE\033[0m: Failed to activate virtual environment"
        exit 1
    fi
else
    echo -e "\033[0;32mOK\033[0m: Virtual environment is already active"
fi

echo -e "Installing project (and dependencies) from pyproject.toml..."
# Upgrade pip tooling (optional but helps with PEP 517/518 builds)
python -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true

# Editable install so changes in src/ are picked up without reinstall
if ! pip install -e .; then
    echo -e "\033[0;31mE\033[0m: Failed to install project from pyproject.toml"
    exit 1
else
    echo -e "\033[0;32mOK\033[0m: Project installed from pyproject.toml"
fi

# Check if playwright was installed and install its dependencies (only if not already done)
if pip show playwright > /dev/null 2>&1; then
    # Check if playwright browsers are already installed
    if [ ! -f ".venv/.playwright_installed" ]; then
        echo -e "[INFO]: Installing Playwright dependencies..."
        if ! playwright install-deps; then
            echo -e "\033[0;31mE\033[0m: Failed to install Playwright dependencies"
            exit 1
        else
            echo -e "\033[0;32mOK\033[0m: Successfully installed Playwright dependencies"
            # Create a marker file to avoid reinstalling
            touch .venv/.playwright_installed
        fi
    else
        echo -e "\033[0;32mOK\033[0m: Playwright dependencies already installed"
    fi
fi

echo -e "\033[0;32mOK\033[0m: All required Python modules are installed."
