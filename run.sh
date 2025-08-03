#!/bin/bash

echo -e ""
echo -e "\033[0;0m┌─||──||──||──||──||─┐\033[1;32m         █     █░ ▄▄▄     ▄▄▄█████▓"
echo -e "\033[0;0m│ \033[1mMonth\033[0m ▒▒▒▒▒▒▒ \033[1m2025\033[0m │\033[1;32m        ▓█░ █ ░█░▒████▄   ▓  ██▒ ▓▒"
echo -e "\033[0;0m├──┬──┬──┬──┬──┬──┬──┤\033[1;32m        ▒█░ █ ░█ ▒██  ▀█▄ ▒ ▓██░ ▒░"
echo -e "\033[0;0m│\033[1mSu\033[0m│\033[1mMo\033[0m│\033[1mTu\033[0m│\033[1mWe\033[0m│\033[1mTh\033[0m│\033[1mFr\033[0m│\033[1mSa\033[0m│\033[1;32m        ░█░ █ ░█ ░██▄▄▄▄██░ ▓██▓ ░"
echo -e "\033[0;0m├──┼──┼──╔══╗──┼──┼──┤\033[1;32m       ░░██▒██▓  ▓█   ▓██▒ ▒██▒ ░"
echo -e "\033[0;0m│▒▒│01│02║03║04│05│06│\033[1;32m       ░ ▓░▒ ▒   ▒▒   ▓▒█░ ▒ ░░"
echo -e "\033[0;0m├──┼──┼──╚══╝──┼──┼──┤\033[1;32m         ▒ ░ ░    ▒   ▒▒ ░   ░"
echo -e "\033[0;0m│07│08│09│10│11│12│13│\033[1;32m         ░   ░    ░   ▒    ░"
echo -e "\033[0;0m├──┼──┼──┼──┼──┼──┼──┤\033[1;32m  ░█▀▀░█▀█░█░░░█▀▀░█▀█░█▀▄░█▀█░█▀▄░█▀▀"
echo -e "\033[0;0m│14│15│16│17│18│19│20│\033[1;32m  ░█░░░█▀█░█░░░█▀▀░█░█░█░█░█▀█░█▀▄░▀▀█"
echo -e "\033[0;0m├──┼──┼──┼──┼──┼──┼──┤\033[1;32m  ░▀▀▀░▀░▀░▀▀▀░▀▀▀░▀░▀░▀▀░░▀░▀░▀░▀░▀▀▀"
echo -e "\033[0;0m│21│22│23│24│25│26│27│\033[1;32m"
echo -e "\033[0;0m├──┼──┼──┼──┼──┼──╔══╗\033[0;0m  Hello \033[1;31m$USER\033[1;0m@\033[1;31m$HOSTNAME\033[0m,"
echo -e "\033[0;0m│28│29│30│31│▒▒│▒▒║03║\033[0;0m  welcome to the \033[0;32mWATcalendars\033[0m project!"
echo -e "\033[0;0m└──┴──┴──┴──┴──┴──╚══╝\033[0;0m  ------------------------"  
echo -e "                        by \033[1mDominik Serafin\033[0m  [\033[4;34mhttps://serafin.byst.re\033[0m]"
echo -e ""
echo -e ""
echo -e "This \033[0;32mopen-source\033[0m project, allows you to \033[1mlearn\033[0m and \033[1mmanage\033[0m scraping scripts."
echo -e "Ready-to-use calendars for your \033[0;32mphone\033[0m can be downloaded from: [\033[4;34mhttps://kalendarze.bieda.it\033[0m]"
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
system_dependencies[python3_binary]="python3"
system_dependencies[pip3_binary]="pip3"
system_dependencies[venv_binary]="python3 -m venv --help"
system_dependencies[python3_packages]="python3"
system_dependencies[pip3_packages]="python3-pip"
system_dependencies[venv_packages]="python3-venv"

missing_system_dependencies=()

# Check python3
if ! command -v "${system_dependencies[python3_binary]}" > /dev/null 2>&1; then
    echo -e "[INFO]: missing python3"
    missing_system_dependencies+=("${system_dependencies[python3_binary]}")
else
    echo -e "[INFO]: found python3"
fi

# Check pip3
if ! command -v "${system_dependencies[pip3_binary]}" > /dev/null 2>&1; then
    echo -e "[INFO]: missing pip3"
    missing_system_dependencies+=("${system_dependencies[pip3_binary]}")
else
    echo -e "[INFO]: found pip3"
fi

# Check python3-venv
if ! command -v "${system_dependencies[venv_binary]}" > /dev/null 2>&1; then
    echo -e "[INFO]: missing python3-venv"
    missing_system_dependencies+=("${system_dependencies[venv_binary]}")
else
    echo -e "[INFO]: found python3-venv"
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
    python3 -m venv venv
    if [ ! -d "venv" ]; then
        echo -e "\033[0;31mE\033[0m: Failed to create virtual environment"
        exit 1
    fi
    echo -e "Activating virtual environment..."
    source venv/bin/activate
    if [ ! -f "venv/bin/activate" ]; then
        echo -e "\033[0;31mE\033[0m: Virtual environment is broken or not created"
        echo -e "Trying to reinstall python3-venv..."
        sudo apt-get install --reinstall python3-venv
        rm -rf venv
        echo -e "Recreating virtual environment..."
        python3 -m venv venv
        echo -e "Activating virtual environment..."
        source venv/bin/activate
        if [ ! -f "venv/bin/activate" ]; then
            echo -e "\033[0;31mE\033[0m: Failed to create or activate virtual environment"
            exit 1
        fi
    else
        echo -e "\033[0;32mOK\033[0m: Virtual environment activated successfully"
    fi
else
    echo -e "[INFO]: Virtual environment found."
    if [ ! -f "venv/bin/activate" ]; then
        echo -e "[INFO]: Virtual environment is broken or not created."
        echo -e "Trying to reinstall python3-venv..."
        sudo apt-get install --reinstall python3-venv
        rm -rf venv
        echo -e "Recreating virtual environment..."
        python3 -m venv venv
        if [ ! -f "venv/bin/activate" ]; then
            echo -e "\033[0;31mE\033[0m: Failed to create or activate virtual environment"
            exit 1
        fi
        echo -e "Activating virtual environment..."
        source venv/bin/activate
        if [ ! -f "venv/bin/activate" ]; then
            echo -e "\033[0;31mE\033[0m: Failed to activate virtual environment"
            exit 1
        fi
    else
        echo -e "\033[0;32mOK\033[0m: Virtual environment is running"
    fi
fi


# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo -e "\033[0;31mE\033[0m: requirements.txt file not found"
    exit 1
fi

# Install Python modules from requirements.txt
echo -e "Installing Python modules from requirements.txt..."
if ! pip3 install -r requirements.txt; then
    echo -e "\033[0;31mE\033[0m: Failed to install Python modules from requirements.txt"
    exit 1
else
    echo -e "\033[0;32mOK\033[0m: Successfully installed Python modules from requirements.txt"
fi

# Check if playwright was installed and install its dependencies
if pip3 show playwright > /dev/null 2>&1; then
    echo -e "[INFO]: Installing Playwright dependencies..."
    if ! playwright install-deps; then
        echo -e "\033[0;31mE\033[0m: Failed to install Playwright dependencies"
        exit 1
    else
        echo -e "\033[0;32mOK\033[0m: Successfully installed Playwright dependencies"
    fi
fi

echo -e "\033[0;32mOK\033[0m: All required Python modules are installed."