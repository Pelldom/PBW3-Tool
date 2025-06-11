PBW3 Tool - User Guide
======================

Author: PellDomPress
pelldom@live.com
Version: 1.02
Graphics: Mark Sedwick (Blackkynight) R.I.P.
---

## What is PBW3 Tool?
PBW3 Tool is a Windows application for automating and managing Play By Web 3 (PBW3) game turns. It streamlines downloading, uploading, and archiving game files for both hosts and players.

---

## System Requirements
- Windows 10 or later
- **One of the following browsers must be installed:**
  - Google Chrome
  - Microsoft Edge
  - Mozilla Firefox
- Internet connection

---

## Installation
1. Run the provided `PBW3ToolSetup.exe` installer.
2. Follow the prompts. The installer will:
   - Install the PBW3 Tool app and required fonts
   - Create Start Menu and Desktop shortcuts
3. On first launch, you will be prompted to select a supported browser if more than one is found.
4. If prompted to reboot for font installation, please do so.

---

## First Launch & Setup
1. Double-click the "PBW3 Tool" shortcut on your Desktop or Start Menu.
2. On first launch, enter your PBW3 username and password.
3. The tool will log in to PBW3 and discover your games.
4. For each game, you may be prompted to select a savegame folder on your computer.
5. The tool will save your configuration in your Windows AppData folder for future use.

---

## Main Features
- **Game List:** Select from your discovered PBW3 games.
- **Run Host Mode:** Download, archive, and upload turns as a game host.
- **Run Player Mode:** Download and upload your player files.
- **Manual Player Upload:** Upload a .plr file manually if needed.
- **Game Settings:** Edit game-specific settings.
- **Log Console:** View progress and error messages.

---

## How to Use
1. Launch the app and select your game from the dropdown.
2. Use the buttons to:
   - Run Host Mode (for hosts)
   - Run Player Mode (for players)
   - Manually upload a .plr file if needed
3. Follow on-screen prompts for downloads, uploads, and confirmations.
4. Check the log console for status updates.

---

## Troubleshooting
- **App does not start:**
  - Make sure you have installed all required files using the installer.
  - Try running the app as Administrator.
- **Fonts look wrong:**
  - Reboot your computer to complete font installation.
- **Cannot log in or download games:**
  - Check your PBW3 credentials.
  - Ensure you have an active internet connection.
- **Browser automation errors:**
  - Make sure you have Chrome, Edge, or Firefox installed. The app will prompt you to select a browser if more than one is found.
  - If you see errors about missing browsers, install one of the supported browsers and restart the app.
- **Config file issues:**
  - The app saves its config in your AppData folder. If you need to reset, delete the `pbw3_config.json` file from `%APPDATA%\PBW3 Tool`.

---

## Uninstalling
- Use "Add or Remove Programs" in Windows, or run the uninstaller from the Start Menu.
- All app files and fonts will be removed.

---

## Credits
- Developed by PellDomPress
- Uses Playwright, BeautifulSoup, and Tkinter
- Icon and splash art by Mark Sedwick (Blackkynight)

---

For support or updates, contact PellDomPress pelldom@live.com or visit the PBW3 community. 