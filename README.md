###### _<div align="right"><sub>// designed by Dominik Serafin</sub></div>_

<div align="center">
  <a href="https://watcalendars.byst.re">
    <img alt="WATcalendars-banner" src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/watcalendars-logo/title-logo.png">
  </a>
</div>

<div align="center">

<a href="#installation"><kbd> Installation </kbd></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="#updating"><kbd> Updating </kbd></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="CONTRIBUTING.md"><kbd> Contributing </kbd></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://watcalendars.byst.re"><kbd> Website </kbd></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://watcalendars.byst.re/index.html#Tutorial"><kbd> Tutorial </kbd></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="https://watcalendars.byst.re/web/Contact.html"><kbd> Contact </kbd></a>&nbsp;&nbsp;&nbsp;&nbsp;
<a href="#support"><kbd> Support </kbd></a>

</div><br><br>

<div align="center">
  <div style="display: flex; flex-wrap: nowrap; justify-content: center;">
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/ioe_logo.png" alt="IOE" style="width: 10%; margin: 30px;"/>
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/wcy_logo.png" alt="WCY" style="width: 10%; margin: 30px;"/>
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/wel_logo.png" alt="WEL" style="width: 10%; margin: 30px;"/>
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/wig_logo.png" alt="WIG" style="width: 10%; margin: 30px;"/>
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/wim_logo.png" alt="WIM" style="width: 10%; margin: 30px;"/>
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/wlo_logo.png" alt="WLO" style="width: 10%; margin: 30px;"/>
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/wml_logo.png" alt="WML" style="width: 10%; margin: 30px;"/>
    <img src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/faculties/logo/wtc_logo.png" alt="WTC" style="width: 10%; margin: 30px;"/>
  </div>
</div>

<br><br>

Check this out for the full note:
[Journey to WATcalendars site](https://watcalendars.byst.re)

<img alt="watcalendars-home-site" src="https://raw.githubusercontent.com/dominikx2002/watcalendars-assets/main/website/home/watcalendars-home.png">
<br>
<br>

<a id="installation"></a>
<img src="https://readme-typing-svg.herokuapp.com?font=Lexend+Giga&size=25&pause=1000&color=32CD32,228B22,006400&vCenter=true&width=435&height=25&lines=INSTALLATION" width="450"/>

---

The installation script is designed for [Arch Linux](https://wiki.archlinux.org/title/Arch_Linux) but **may** also work on some [Arch-based distros](https://wiki.archlinux.org/title/Arch-based_distributions).

The setup script includes logic to **detect your Linux distribution** and automatically install the required system dependencies for that distro. It currently supports:

- **Debian/Ubuntu-based distributions** (Ubuntu, Debian, Pop!_OS, Linux Mint, etc.)
- **Fedora/CentOS/RHEL/Rocky/AlmaLinux**
- **Arch Linux and derivatives** (Manjaro, EndeavourOS)
- **openSUSE, Alpine Linux**

This ensures that the necessary packages like `python3`, `pip3`, and `python3-venv` are installed correctly, no matter which supported distribution you are using.

More informations about dependencies:
[Journey to dependencies](https://watcalendars.byst.re/web/Dependencies.html)

> [!IMPORTANT]
> The setup script will also install python dependencies like playwright and bs4.  
> Playwright may **not work** on some distributions.  

> [!CAUTION]
> The script will **modify your system packages** to install missing dependencies.  
> Please review the script if you are using a custom or unsupported Linux distribution.

### To install WATcalendars project including python scripts:

Clone the repository to your local machine.

```shell
git clone https://github.com/dominikx2002/WATcalendars.git
```

Add rights to the setup script.

```shell
cd WATcalendars && chmod +x setup.sh
```

Run following script to autmaticaly install required dependencies.

```shell
./setup.sh
```

#### After that, welcome-text will pop up on your console:
<div align="center">
    <img width="963" height="569" alt="screely-1759080562632" src="https://github.com/user-attachments/assets/19c261b4-9c9c-4061-934b-218116268ff7" />
</div>

#### The setup script will ask you several questions during the installation process, answer these prompts to allow the script to install the required dependencies automatically.

> [!IMPORTANT]
> After running the setup script, you can use the scraping scripts, modify them, customize them, and fix as needed.  
> Check the `"help.txt"` file in the repository for available options and useful information.

> [!TIP]
> To view the help file, run the following command in your terminal:
>
> ```bash
> cat help.txt
> ```
> This will display all available commands and options for the WATcalendars project.



<br>
<br>
<br>
<br>
<a id="contributing"></a>
<img src="https://readme-typing-svg.herokuapp.com?font=Lexend+Giga&size=25&pause=1000&color=32CD32,228B22,006400&vCenter=true&width=435&height=25&lines=CONTRIBUTING" width="450"/>

---

We welcome contributions from the community! To get started:

- Check our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.
- Report issues, suggest features, or help improve the scraping scripts.
- Help with documentation, examples, or testing.

Whether you're contributing code, improving the documentation, or testing features, we appreciate your support in making **WATcalendars** better for everyone. Thank you!



<br>
<br>
<br>
<br>
<a id="updating"></a>
<img src="https://readme-typing-svg.herokuapp.com?font=Lexend+Giga&size=25&pause=1000&color=32CD32,228B22,006400&vCenter=true&width=435&height=25&lines=UPDATING" width="450"/>

---

Keeping your **WATcalendars** installation up-to-date is important to ensure you have the latest scripts, features, and bug fixes.

> [!TIP]
> To update your local repository, simply navigate to your WATcalendars folder and pull the latest changes:
>
> ```bash
> cd WATcalendars
> git pull origin main
> ```

> [!IMPORTANT]
> After updating, it is recommended to **re-run the setup script** to ensure all dependencies are up-to-date:
>
> ```bash
> ./setup.sh
> ```

> [!TIP]
> If you are using a virtual environment, make sure it is activated before running the setup script:
>
> ```bash
> source .venv/bin/activate
> ```



<br>
<br>
<br>
<a id="support"></a>
<img src="https://readme-typing-svg.herokuapp.com?font=Lexend+Giga&size=25&pause=1000&color=32CD32,228B22,006400&vCenter=true&width=435&height=25&lines=SUPPORT" width="450"/>

---
<div align="center">

  ### ☕ Support WATcalendars on Buy Me a Coffee

  If you like this project and want to support its development, consider buying me a coffee:

  <a href="https://www.buymeacoffee.com/dominikx2002" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px; width: 217px;">
  </a>
  
<br><br>

also consider sponsoring me on GitHub:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/sponsors/dominikx2002)

</div>








