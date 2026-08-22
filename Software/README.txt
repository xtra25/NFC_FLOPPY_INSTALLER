===================================================================
NFC Game Launcher (Steam, GOG, ScummVM) - Self-Installing Edition
===================================================================

This project uses an NFC reader and cards (or floppy disks equipped with NFC chips) to automatically launch Steam, GOG, and ScummVM games in a Windows environment. It is designed to run transparently in the background, allowing non-admin users to launch games simply by tapping a card against the reader.

ARCHITECTURE & DESIGN DECISIONS
-----------------------------------
- Self-Installation: The script detects if it is running from its target folder (C:\NFC_Launcher). If not, it requests UAC elevation and installs itself automatically.
- Background Execution: Uses 'pythonw.exe' to run silently without active consoles. Generates an activity log at C:\NFC_Launcher\nfc_launcher.log.
- Global Autostart: Creates a .bat file in the StartUp folder for all users (%ALLUSERSPROFILE%). This ensures the NFC monitor starts regardless of the user logging in.
- Permission Management (icacls): The script grants full permissions (Modify/Write) to the universal "Users" group on the designated games folder (e.g., C:\FloppyGames) and adjusts the Steam folder to prevent UAC blocks on standard accounts.

SYSTEM REQUIREMENTS
-----------------------------------
1. Operating System: Windows 10/11.
2. Python: Python 3.x installed and added to the system 'PATH'.
3. NFC Reader: Any PC/SC compliant smart card reader (e.g., ACR122U readers).
4. Dependencies: The 'pyscard' library (the script installs it automatically during the first run if not found).

INSTALLATION AND INITIAL SETUP
-----------------------------------
The installation process is fully automated:

1. Download 'nfc_launcher.py' (and optionally 'floppy_disks.json' or 'gog_catalog_full.json') to a temporary folder.
2. Double-click on 'nfc_launcher.py'.
3. Windows will ask for administrator permissions (UAC). Accept them.
4. The script will copy itself to C:\NFC_Launcher, configure permissions, set up autostart, and launch the background service. Once finished, you can delete the original downloaded file.

Mandatory Manual Configuration for Steam:
To prevent corruption of internal Steam .vdf files, two settings must be adjusted in the client:
- Storage: Go to Settings -> Storage and add the configured path (e.g., C:\FloppyGames). Click the three dots and set it as "Default".
- Sign In: Go to Settings -> Interface and DISABLE "Ask which account to use each time Steam starts". This will prevent the process from getting stuck when launching a game via NFC.

NFC DATA FORMAT
-----------------------------------
The script reads the NFC tag's memory blocks looking for printable ASCII text. Supported formats:

- Steam (Direct ID): STEAM:12345 (where 12345 is the Steam AppID).
- GOG (Direct ID): GOG:1234567890 (where 1234567890 is the GOG GameID).
- ScummVM (Short ID): SCUMM:tentacle (where tentacle is the internal ID within ScummVM).
- Auto-discovery (Numbers only): 12345 (The script will first query GOG and then Steam to discover which platform it belongs to and retrieve its name).

GENERATED FILES
-----------------------------------
- floppy_disks.json: Generated inside C:\NFC_Launcher. Acts as a local cache database linking IDs to real game names.
- nfc_launcher.log: Activity and error log file for the background service.

UNINSTALLATION
-----------------------------------
To completely remove the process and clean up the system, use the uninstallation script ('uninstall.py'):

1. Run 'uninstall.py' (it will ask for administrator permissions).
2. The script will stop the 'pythonw.exe' processes associated with the NFC monitor.
3. It will delete the autostart file from the system.
4. It will ask if you want to completely delete the installation folder (C:\NFC_Launcher), including logs and the database.

The folders where the games are hosted (e.g., C:\FloppyGames) remain intact for safety.