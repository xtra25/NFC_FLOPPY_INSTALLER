===================================================================
NFC Game Launcher (Steam, GOG, ScummVM) - Self-Installing Edition
Version 2.3
===================================================================

This project uses an NFC reader and cards (or floppy disks equipped with NFC
chips) to automatically launch Steam, GOG, and ScummVM games in a Windows
environment. It runs transparently in the background, allowing users to launch
games simply by tapping a card against the reader.

*** IMPORTANT: version 2.x changes the installation model. ***
See "UPGRADING FROM VERSION 1.x" at the end of this file.


ARCHITECTURE & DESIGN DECISIONS
-----------------------------------
- Per-user installation, no UAC. The script installs into the current user's
  profile (%LOCALAPPDATA%\Programs\NFC_Launcher) and never requests elevation.
  Each user who wants the reader runs the installer once with their own
  account. This replaces the old machine-wide install in C:\NFC_Launcher.

- The background service must NOT run elevated. An elevated service reads the
  wrong HKEY_CURRENT_USER and %APPDATA%, which makes ScummVM open with the
  administrator's empty game library and Steam inspect the wrong profile. If
  the installer is deliberately run as administrator, it starts the service
  de-elevated through explorer.exe so the user context stays correct.

- Per-user autostart. The .bat file goes in the current user's Startup folder
  (%APPDATA%), not the all-users one. Writing to the all-users folder was the
  only reason the old installer needed administrator rights.

- Per-user data. The log and the game-name cache live in
  %LOCALAPPDATA%\NFC_Launcher, separate from the program folder. If the log
  cannot be opened the service falls back to %TEMP% instead of dying silently
  under pythonw.exe.

- Launching never depends on the network. A game is launched from the card's
  ID and platform alone. Name lookups happen after the launch and only enrich
  the local cache; if the Steam API is rate-limited or returns success:false,
  the game still starts.

- Protocol URIs are launched de-elevated via explorer.exe. Protocols such as
  steam:// are registered under HKEY_CURRENT_USER, so a high-integrity process
  cannot resolve them and the launch fails silently.

- ScummVM detection is restricted to the official scummvm.org build, located
  through the Inno Setup uninstall key "ScummVM_is1". Copies bundled inside GOG
  games and portable builds do not create that key and are ignored.

- The installer is also the uninstaller. Run it again and it detects the
  existing installation, then offers to uninstall, reinstall/update, or exit.


SYSTEM REQUIREMENTS
-----------------------------------
1. Operating System: Windows 10/11.
2. Python 3.x. On multi-user machines install it with "Install for all users",
   otherwise each user needs their own Python installation.
3. NFC Reader: any PC/SC compliant smart card reader (e.g. ACR122U).
4. Dependencies: 'pyscard' (installed automatically on first run if missing).


INSTALLATION
-----------------------------------
1. Download 'nfc_launcher.py' (and optionally 'floppy_disks.json' or
   'gog_catalog_full.json') to any folder.
2. Run pyhton 'nfc_launcher.py'.
3. Choose the language. No UAC prompt appears.
4. The script copies itself to %LOCALAPPDATA%\Programs\NFC_Launcher, sets up
   autostart for this user, and starts the background service.
5. Repeat for each user account that should have the reader.


COMMAND-LINE OPTIONS
-----------------------------------
  (no arguments)   Install, or show the install/uninstall menu if already
                   installed.
  --diag           Print a diagnostic report: user context, ScummVM
                   executable and .ini with its configured games, Steam
                   libraries, and the two known causes of UAC prompts.
                   Run this as the affected user, NOT as administrator.
  --prep           Prepare Steam prerequisites. Requires administrator.
  --fix-redist     Same as --prep. Requires administrator.
  --background     Used internally by the autostart .bat.
  --lang en|ca     Skip the language prompt.


STEAM: FIRST-LAUNCH UAC PROMPTS
-----------------------------------
Installing a Steam game never needs administrator rights. The prompt some
users see on a game's FIRST launch comes from the prerequisite installers
(Visual C++, DirectX, .NET) that Steam runs at that moment. Folder permissions
cannot prevent it; those installers are manifested requireAdministrator.

There are two things to check, and --diag reports both:

1. Steam Client Service must be RUNNING. This service runs as SYSTEM and is
   Valve's own mechanism for installing prerequisites without a UAC prompt.

2. The CommonRedist registry keys must not be mismatched. Steam records
   installed prerequisites under
   HKLM\SOFTWARE\Valve\Steam\Apps\CommonRedist. Because the client was
   historically 32-bit, Windows redirected its writes to WOW6432Node while
   part of the client reads the non-redirected path. Steam then never finds
   the "already installed" marker and re-runs the installer every time.

Run '--prep' once as an administrator to fix both. It also runs any pending
prerequisites through 'steamservice.exe /installscript', which is Steam's own
mechanism: it knows the correct silent switches for each installer and writes
the hasrunkey marker, so Steam stops re-running them.

Note: games with kernel-level anti-cheat (EasyAntiCheat, BattlEye) install a
driver on first launch. That always requires administrator and cannot be
automated away.


STEAM: MANUAL CONFIGURATION
-----------------------------------
The script deliberately never writes to Steam's .vdf configuration files.
Configure these in the client yourself:

- Storage: Settings -> Storage. Add your games folder if you want one, and use
  the three dots to set it as Default. This is optional; it has no effect on
  UAC prompts.

- Sign In: Settings -> Interface. DISABLE "Ask which account to use each time
  Steam starts", or Steam may block on the account-selection screen when a
  game is launched via NFC.


NFC DATA FORMAT
-----------------------------------
The script reads the tag's memory blocks looking for printable ASCII text.

- Steam:   STEAM:12345         (12345 = Steam AppID)
- GOG:     GOG:1234567890      (1234567890 = GOG GameID)
- ScummVM: SCUMM:tentacle      (tentacle = ScummVM target ID)
- EA:      EA:123456           (EA App offer ID)
- Minecraft: any tag containing the word MINECRAFT
- Auto-discovery: 12345        (queries GOG then Steam to identify it)

Explicit prefixes are strongly recommended. Auto-discovery is the only path
that genuinely requires an internet connection.

For SCUMM tags, the target ID must exist in that user's scummvm.ini. The
script checks this before launching and reports the available targets in the
log if it does not match.


GENERATED FILES
-----------------------------------
%LOCALAPPDATA%\Programs\NFC_Launcher\
    nfc_launcher.py      The installed script.
    floppy_disks.json    Read-only seed cache, if one was shipped alongside.

%LOCALAPPDATA%\NFC_Launcher\
    nfc_launcher.log     Activity and error log for the background service.
    floppy_disks.json    Per-user cache mapping IDs to real game names.

%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
    NFC_Floppy_AutoStart.bat


UNINSTALLATION
-----------------------------------
Run 'nfc_launcher.py' again and choose option 1. No UAC prompt. It stops the
service, removes the autostart entry, deletes the program folder, and asks
separately whether to also delete the log and the game cache.

The service is located by command line, not by process name, so other Python
scripts are never terminated.


UPGRADING FROM VERSION 1.x
-----------------------------------
Version 1.x installed machine-wide into C:\NFC_Launcher with an autostart
entry in the all-users Startup folder. Those files are NOT removed by the new
per-user uninstaller, and if left in place they keep starting the old copy at
every login, giving you two services competing for the same reader.

The script detects these leftovers and reports their exact paths in --diag and
after installing. To remove them, run 'uninstall.py' once as an administrator;
it is kept in this repository only for that cleanup.

Recommended order:
  1. As an administrator, run 'uninstall.py' to remove the old machine-wide
     installation.
  2. As an administrator, run 'nfc_launcher.py --fix-redist' once. This
     affects the whole machine and covers every user.
  3. As each user, run 'nfc_launcher.py' to install for that account.
