# ===================================================================
# NFC Game Launcher - Self-Installing Edition
# Copyright (C) 2026
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# ===================================================================
#
# Version: 2.3
#
# ===================================================================

APP_VERSION = "2.3"

import os
import sys
import subprocess
import json
import time
import winreg
import re
import urllib.request
import urllib.error
import shutil
import ctypes
import importlib

# ===================================================================
# SISTEMA D'IDIOMES (I18N)
# ===================================================================
TEXTS = {
    'en': {
        'req_admin': "[INFO] Administrator privileges required for installation. Requesting...",
        'install_start': " [INSTALL] Starting system installation...",
        'copy_script': " -> Script copied to:",
        'copy_db': " -> Database copied:",
        'autostart_configured': " -> Global autostart configured successfully.",
        'autostart_failed': "[WARNING] Could not configure autostart:",
        'install_success': " [SUCCESS] Installation completed successfully!",
        'service_running': " [INFO] The service is now running in the background. Log file at",
        'delete_original': " >>> YOU CAN NOW DELETE THIS ORIGINAL FILE:",
        'press_enter_close': "Press Enter to close this window...",
        'mc_init': "[PLATFORM: MINECRAFT] Launching...",
        'mc_launched_store': " -> Launched Minecraft Launcher (Store/Xbox App)",
        'mc_classic': " -> Launched classic launcher: ",
        'mc_uri': " -> Launched via 'minecraft:' protocol",
        'mc_store': " -> Launcher not found. Opening Store to download it...",
        'mc_err': "[ERROR] Launching Minecraft: ",
        'already_installed': "NFC Game Launcher is already installed for this user",
        'ai_folder': "Folder   :",
        'ai_autostart': "Autostart:",
        'ai_service': "Service  :",
        'opt_uninstall': "Uninstall",
        'opt_reinstall': "Reinstall / update",
        'opt_exit': "Exit without changes",
        'opt_prompt': "Option [1/2/3]:",
        'reinstalling': "Reinstalling...",
        'uninstall_start': "UNINSTALLING NFC Game Launcher",
        'uninstall_stopping': "Stopping the service...",
        'uninstall_autostart': "Removing autostart entry...",
        'uninstall_program': "Removing program folder...",
        'uninstall_data_q': "Data (log and game cache):",
        'uninstall_data_prompt': "Delete them too? [y/N]:",
        'uninstall_done': "Uninstalled. Nothing will start at next login.",
        'service_as_user': "[OK] Service started as the interactive user (de-elevated).",
        'service_elevated_warn': "[WARNING] Service started ELEVATED. On multi-user PCs it may read the wrong profile. Reboot to fix it.",
    },
    'ca': {
        'req_admin': "[INFO] Es requereixen permisos d'administrador per instal·lar. Sol·licitant-los...",
        'install_start': " [INSTALL] Iniciant instal·lació al sistema...",
        'copy_script': " -> Còpia de l'script a:",
        'copy_db': " -> Còpia de la base de dades:",
        'autostart_configured': " -> Auto-arrencada global configurada correctament.",
        'autostart_failed': "[WARNING] No s'ha pogut configurar l'auto-arrencada:",
        'install_success': " [SUCCESS] Instal·lació completada amb èxit!",
        'service_running': " [INFO] El servei ja corre en segon pla. L'arxiu log està a",
        'delete_original': " >>> JA POTS ESBORRAR AQUEST FITXER ORIGINAL:",
        'press_enter_close': "Prem Enter per tancar aquesta finestra...",
        'mc_init': "[PLATFORM: MINECRAFT] Llançant...",
        'mc_launched_store': " -> Llançat Minecraft Launcher (Store/Xbox App)",
        'mc_classic': " -> Llançat el launcher clàssic: ",
        'mc_uri': " -> Llançat via protocol 'minecraft:'",
        'mc_store': " -> No s'ha trobat el launcher. Obrint la Store per descarregar-lo...",
        'mc_err': "[ERROR] Llançant Minecraft: ",
        'already_installed': "NFC Game Launcher ja esta instal.lat per a aquest usuari",
        'ai_folder': "Carpeta    :",
        'ai_autostart': "Autoarrencada:",
        'ai_service': "Servei     :",
        'opt_uninstall': "Desinstal.lar",
        'opt_reinstall': "Reinstal.lar / actualitzar",
        'opt_exit': "Sortir sense canvis",
        'opt_prompt': "Opcio [1/2/3]:",
        'reinstalling': "Reinstal.lant...",
        'uninstall_start': "DESINSTAL.LANT NFC Game Launcher",
        'uninstall_stopping': "Aturant el servei...",
        'uninstall_autostart': "Traient l'autoarrencada...",
        'uninstall_program': "Esborrant la carpeta del programa...",
        'uninstall_data_q': "Dades (log i cache de jocs):",
        'uninstall_data_prompt': "Les esborrem tambe? [s/N]:",
        'uninstall_done': "Desinstal.lat. Al proper inici no arrencara res.",
        'service_as_user': "[OK] Servei arrencat com a usuari interactiu (de-elevat).",
        'service_elevated_warn': "[AVIS] Servei arrencat ELEVAT. En PCs amb varis usuaris pot llegir el perfil equivocat. Reinicia per corregir-ho.",
    }
}

lang = 'ca' 

def T(key):
    return TEXTS.get(lang, TEXTS['ca']).get(key, key)

if "--lang" in sys.argv:
    try:
        lang = sys.argv[sys.argv.index("--lang") + 1]
    except IndexError:
        pass

# ===================================================================
# CONFIGURACIÓ DE RUTES D'INSTAL·LACIÓ
# ===================================================================
# -------------------------------------------------------------------
# INSTAL.LACIO PER USUARI (sense privilegis d'administrador)
# Tot viu dins del perfil de l'usuari, aixi que la instal.lacio no
# necessita UAC en cap moment. Cada usuari que vulgui el lector passa
# l'instal.lador un cop amb el seu propi compte.
# -------------------------------------------------------------------
INSTALL_DIR = os.path.join(
    os.getenv("LOCALAPPDATA") or os.path.expanduser("~"),
    "Programs", "NFC_Launcher"
)
INSTALL_FILE = os.path.join(INSTALL_DIR, "nfc_launcher.py")

# -------------------------------------------------------------------
# Dades per usuari: log i cache. Separades del directori del script
# perque el script es un fitxer de programa i aixo son dades variables.
# -------------------------------------------------------------------
def _get_user_data_dir():
    for base in [os.getenv("LOCALAPPDATA"), os.getenv("APPDATA"), os.getenv("TEMP")]:
        if base:
            d = os.path.join(base, "NFC_Launcher")
            try:
                os.makedirs(d, exist_ok=True)
                prova = os.path.join(d, ".write_test")
                with open(prova, "w") as f:
                    f.write("ok")
                os.remove(prova)
                return d
            except Exception:
                continue
    return INSTALL_DIR  # ultim recurs

USER_DATA_DIR = _get_user_data_dir()
LOG_FILE = os.path.join(USER_DATA_DIR, "nfc_launcher.log")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cache compartida (nomes lectura) i cache de l'usuari (lectura/escriptura)
SHARED_DISKS_FILE = os.path.join(BASE_DIR, "floppy_disks.json")
FLOPPY_DISKS_FILE = os.path.join(USER_DATA_DIR, "floppy_disks.json")
GOG_CATALOG_FILE = os.path.join(BASE_DIR, "gog_catalog_full.json")

# ===================================================================
# 1. DEPENDÈNCIES I PRIVILEGIS
# ===================================================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_privileges():
    """
    Rellanca el script elevat CONSERVANT els arguments originals.

    Abans nomes es passava --lang, aixi que qualsevol altre flag (--prep,
    --fix-redist, --diag) es perdia en elevar: l'usuari posava la contrasenya
    i el proces elevat feia la instal.lacio normal en comptes de la feina
    demanada, sense cap error visible.
    """
    if not is_admin():
        print(T('req_admin'))

        # Passem els arguments tal com han vingut i nomes hi afegim --lang
        # si no hi era. Res de reconstruir-los: aixi no es pot perdre cap flag.
        args = list(sys.argv[1:])
        if not any(a == "--lang" or a.startswith("--lang=") for a in args):
            args += ["--lang", lang]

        params = " ".join(
            [f'"{os.path.abspath(__file__)}"'] +
            [f'"{a}"' if " " in a else a for a in args]
        )
        print(f"    (rellancant elevat amb: {params})")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        sys.exit(0)

def check_and_install_dependencies():
    try:
        import smartcard
    except ImportError:
        print("[STARTUP] Missing 'pyscard'. Installing... / Instal·lant...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyscard"])
            importlib.invalidate_caches()
            print("[STARTUP] 'pyscard' Installed / Instal·lat.\n")
        except subprocess.CalledProcessError as e:
            print(f"[CRITICAL ERROR] Dependency fail: {e}")
            input("Press Enter to exit...")
            sys.exit(1)

check_and_install_dependencies()
from smartcard.CardMonitoring import CardMonitor, CardObserver

# ===================================================================
# 2. INSTAL·LACIÓ I CONFIGURACIÓ
# ===================================================================

def get_autostart_path():
    """Ruta del .bat d'autoarrencada de l'usuari actual."""
    return os.path.join(
        os.getenv('APPDATA', ''),
        r'Microsoft\Windows\Start Menu\Programs\Startup',
        "NFC_Floppy_AutoStart.bat"
    )

def find_service_pids():
    """
    PIDs del servei en marxa (pythonw.exe executant aquest script).

    tasklist no dona la linia d'ordres, aixi que no serveix per distingir el
    nostre pythonw d'un altre. Fem servir CIM, i si falla provem WMIC.
    """
    pids = []

    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' or "
        "Name='python.exe'\" | Where-Object { $_.CommandLine -like "
        "'*nfc_launcher*' -and $_.ProcessId -ne %d } | "
        "Select-Object -ExpandProperty ProcessId"
    ) % os.getpid()

    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30
        )
        for linia in (out.stdout or "").split():
            if linia.strip().isdigit():
                pids.append(int(linia.strip()))
    except Exception:
        pass

    if not pids:
        try:
            out = subprocess.run(
                ["wmic", "process", "where",
                 "name='pythonw.exe' or name='python.exe'",
                 "get", "processid,commandline", "/format:csv"],
                capture_output=True, text=True, timeout=30
            )
            for linia in (out.stdout or "").splitlines():
                if "nfc_launcher" not in linia.lower():
                    continue
                cols = linia.strip().split(",")
                if cols and cols[-1].strip().isdigit():
                    pid = int(cols[-1].strip())
                    if pid != os.getpid():
                        pids.append(pid)
        except Exception:
            pass

    return sorted(set(pids))

def is_already_installed():
    """Hi ha una instal.lacio per a aquest usuari?"""
    return os.path.exists(INSTALL_FILE) or os.path.exists(get_autostart_path())

def stop_service():
    """Atura el servei en marxa. Retorna quants processos ha tancat."""
    pids = find_service_pids()
    aturats = 0
    for pid in pids:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, timeout=15)
            aturats += 1
        except Exception as e:
            print(f"    (no s'ha pogut aturar el PID {pid}: {e})")
    return aturats

def uninstall_from_system():
    """
    Desinstal.la per a l'usuari actual. No cal UAC: tot viu al seu perfil.
    """
    print("\n" + "=" * 70)
    print(T('uninstall_start'))
    print("=" * 70)

    print(f"\n[1/4] {T('uninstall_stopping')}")
    n = stop_service()
    print(f"      {n} proces(sos) aturats.")

    print(f"\n[2/4] {T('uninstall_autostart')}")
    bat = get_autostart_path()
    if os.path.exists(bat):
        try:
            os.remove(bat)
            print(f"      Esborrat: {bat}")
        except Exception as e:
            print(f"      [ERROR] {e}")
    else:
        print("      (no hi era)")

    print(f"\n[3/4] {T('uninstall_program')}")
    if os.path.isdir(INSTALL_DIR):
        try:
            # Si ens estem executant des d'aqui, Python ja ha tancat el fitxer
            # font, pero el __pycache__ pot quedar bloquejat: ignorem errors
            # parcials i informem del que quedi.
            shutil.rmtree(INSTALL_DIR, ignore_errors=True)
            if os.path.isdir(INSTALL_DIR):
                print(f"      [AVIS] No s'ha pogut esborrar del tot:")
                print(f"             {INSTALL_DIR}")
                print(f"             Esborra-la a ma despres de tancar aixo.")
            else:
                print(f"      Esborrada: {INSTALL_DIR}")
        except Exception as e:
            print(f"      [ERROR] {e}")
    else:
        print("      (no hi era)")

    print(f"\n[4/4] {T('uninstall_data_q')}")
    print(f"      {USER_DATA_DIR}")
    resposta = input(f"      {T('uninstall_data_prompt')} ").strip().lower()
    if resposta in ("s", "si", "sí", "y", "yes"):
        try:
            shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
            print("      Esborrades.")
        except Exception as e:
            print(f"      [ERROR] {e}")
    else:
        print("      Conservades.")

    check_old_install()

    print("\n" + "=" * 70)
    print(T('uninstall_done'))
    print("=" * 70)
    input(f"\n{T('press_enter_close')}")
    sys.exit(0)

def check_old_install():
    """
    Avisa de restes de la instal.lacio antiga (a tot el sistema).

    Si no es treuen, el .bat de la carpeta StartUp compartida seguiria
    arrencant la copia vella de C:\\NFC_Launcher a cada login, i tindries dos
    serveis llegint el mateix lector NFC.
    """
    restes = []

    bat_antic = os.path.join(
        os.getenv('ALLUSERSPROFILE', ''),
        r'Microsoft\Windows\Start Menu\Programs\StartUp',
        "NFC_Floppy_AutoStart.bat"
    )
    if os.path.exists(bat_antic):
        restes.append(bat_antic)

    if os.path.isdir(r"C:\NFC_Launcher"):
        restes.append(r"C:\NFC_Launcher")

    if restes:
        print("\n" + "=" * 70)
        print("[AVIS] S'ha detectat una instal.lacio antiga a tot el sistema.")
        print("       Cal esborrar-la a ma (requereix administrador) o tindras")
        print("       dos serveis llegint el mateix lector:")
        for r in restes:
            print(f"         - {r}")
        print("=" * 70)
    return restes

def install_to_system():
    # Sense elevate_privileges(): tot el que fem viu dins del perfil de
    # l'usuari, aixi que no cal UAC en cap moment.
    print("\n" + "=" * 70)
    print(T('install_start'))
    print("=" * 70)

    os.makedirs(INSTALL_DIR, exist_ok=True)

    current_file = os.path.abspath(__file__)
    if current_file.lower() != INSTALL_FILE.lower():
        shutil.copy2(current_file, INSTALL_FILE)
        print(f"{T('copy_script')} {INSTALL_FILE}")

        for json_file in ["floppy_disks.json", "gog_catalog_full.json"]:
            src_json = os.path.join(BASE_DIR, json_file)
            if os.path.exists(src_json):
                shutil.copy2(src_json, os.path.join(INSTALL_DIR, json_file))
                print(f"{T('copy_db')} {json_file}")

    autostart_bat = setup_windows_autostart(INSTALL_FILE)

    # La instal.lacio ja corre com l'usuari normal, aixi que el servei hereta
    # el context correcte directament. Nomes si algu executa l'instal.lador
    # elevat a proposit fem servir explorer.exe per de-elevar-lo: un servei
    # elevat llegiria el HKCU i el %APPDATA% equivocats (ScummVM sense jocs).
    pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable

    if is_admin() and autostart_bat and os.path.exists(autostart_bat):
        subprocess.Popen(["explorer.exe", autostart_bat])
        print(T('service_as_user'))
    else:
        subprocess.Popen([pythonw_exe, INSTALL_FILE, "--background"])
        print(T('service_as_user'))

    print("\n" + "=" * 70)
    print(T('install_success'))
    print(f"{T('service_running')} {LOG_FILE}")
    print(f"\n{T('delete_original')} {current_file}")
    print("=" * 70)

    check_old_install()

    input(f"\n{T('press_enter_close')}")
    sys.exit(0)

def setup_windows_autostart(target_script):
    """
    Autoarrencada NOMES per a l'usuari actual.

    Abans s'escrivia a la carpeta StartUp de tots els usuaris
    (%ALLUSERSPROFILE%), i aixo era l'unic motiu pel qual la instal.lacio
    necessitava UAC. La carpeta de l'usuari no en necessita, i a mes evita
    apuntar altres comptes a un Python que potser no poden ni llegir.
    """
    try:
        startup_folder = os.path.join(
            os.getenv('APPDATA'),
            r'Microsoft\Windows\Start Menu\Programs\Startup'
        )
        os.makedirs(startup_folder, exist_ok=True)
        launcher_file = os.path.join(startup_folder, "NFC_Floppy_AutoStart.bat")
        pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw_exe):
            pythonw_exe = sys.executable

        bat_content = f'@echo off\nstart "" "{pythonw_exe}" "{target_script}" --background\n'

        with open(launcher_file, "w", encoding="utf-8") as f:
            f.write(bat_content)
        print(T('autostart_configured'))
        return launcher_file
    except Exception as e:
        print(f"{T('autostart_failed')} {e}")
        return None

def is_steam_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
            capture_output=True, text=True
        )
        return "steam.exe" in (out.stdout or "").lower()
    except Exception:
        return False

def get_steam_service_state():
    """
    Estat del 'Steam Client Service'.

    Aquest servei corre com a SYSTEM i es el mecanisme que Valve va dissenyar
    precisament perque Steam pugui instal.lar prerequisits (Visual C++,
    DirectX...) SENSE que salti l'UAC. Si esta aturat o desactivat, Steam ha
    de demanar elevacio a l'usuari, i un usuari estandard no la pot donar.
    """
    try:
        out = subprocess.run(
            ["sc", "query", "Steam Client Service"],
            capture_output=True, text=True, timeout=15
        )
        text = (out.stdout or "") + (out.stderr or "")
        for estat in ["RUNNING", "STOPPED", "START_PENDING", "PAUSED"]:
            if estat in text.upper():
                return estat
        if "1060" in text or "does not exist" in text.lower():
            return "NO INSTAL.LAT"
        return "DESCONEGUT"
    except Exception as e:
        return f"ERROR ({e})"

def check_commonredist_registry():
    """
    Detecta el desajust de claus que fa que Steam reinstal.li els prerequisits
    cada vegada (i per tant demani UAC cada vegada).

    Steam marca els prerequisits ja instal.lats amb claus a
    HKLM\\SOFTWARE\\Valve\\Steam\\Apps\\CommonRedist. Com que el client ha
    estat historicament de 32 bits, Windows redirigeix les seves escriptures a
    HKLM\\SOFTWARE\\WOW6432Node\\..., pero part del client busca la clau a la
    ruta sense redirigir. Resultat: no troba mai la marca i torna a llancar
    l'instal.lador, amb el seu UAC corresponent.
    """
    base = r"SOFTWARE\Valve\Steam\Apps\CommonRedist"

    def existeix(flags):
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0,
                               winreg.KEY_READ | flags)
            n = winreg.QueryInfoKey(k)[0]
            winreg.CloseKey(k)
            return n
        except OSError:
            return None

    n64 = existeix(winreg.KEY_WOW64_64KEY)   # ruta sense redirigir
    n32 = existeix(winreg.KEY_WOW64_32KEY)   # WOW6432Node

    if n32 and not n64:
        return (f"DESAJUST ({n32} a WOW6432Node, 0 a la ruta directa) "
                f"-> executa amb --fix-redist")
    if n64 and n32:
        return f"OK ({n64} directes / {n32} a WOW6432Node)"
    if n64:
        return f"OK ({n64} entrades)"
    return "cap entrada (encara no s'ha instal.lat cap prerequisit)"

def fix_commonredist_registry():
    """
    Copia les claus de CommonRedist de WOW6432Node a la ruta sense redirigir,
    perque Steam les trobi i deixi de reinstal.lar els prerequisits.
    Requereix privilegis d'administrador (escriu a HKLM).
    """
    base = r"SOFTWARE\Valve\Steam\Apps\CommonRedist"
    copiades = 0

    def copia_recursiva(origen, desti):
        nonlocal copiades
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(origen, i)
            except OSError:
                break
            i += 1
            try:
                o = winreg.OpenKey(origen, sub, 0,
                                   winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
                d = winreg.CreateKeyEx(desti, sub, 0,
                                       winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY)
                j = 0
                while True:
                    try:
                        nom, dada, tipus = winreg.EnumValue(o, j)
                    except OSError:
                        break
                    j += 1
                    winreg.SetValueEx(d, nom, 0, tipus, dada)
                copiades += 1
                copia_recursiva(o, d)
                winreg.CloseKey(o)
                winreg.CloseKey(d)
            except OSError as e:
                print(f"    (omesa '{sub}': {e})")

    try:
        origen = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
    except OSError:
        print("[AVIS] No hi ha claus a WOW6432Node: res a copiar.")
        return

    try:
        desti = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, base, 0,
                                   winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY)
    except OSError as e:
        print(f"[ERROR] No s'ha pogut crear la clau desti (cal ser admin): {e}")
        return

    copia_recursiva(origen, desti)
    winreg.CloseKey(origen)
    winreg.CloseKey(desti)
    print(f"[OK] {copiades} claus copiades a la ruta sense redirigir.")

def _steam_appid_map(biblioteques):
    """
    Mapa carpeta-del-joc -> appid, llegint els appmanifest_*.acf.
    Cal per poder dir-li a steamservice a quin joc pertany cada installscript.
    """
    mapa = {}
    for lib in biblioteques:
        if not os.path.isdir(lib):
            continue
        for f in os.listdir(lib):
            if not (f.startswith("appmanifest_") and f.endswith(".acf")):
                continue
            try:
                with open(os.path.join(lib, f), "r", encoding="utf-8",
                          errors="ignore") as fh:
                    txt = fh.read()
                appid = re.search(r'"appid"\s+"(\d+)"', txt)
                instdir = re.search(r'"installdir"\s+"([^"]+)"', txt)
                if appid and instdir:
                    mapa[instdir.group(1).lower()] = appid.group(1)
            except Exception:
                pass
    return mapa

def _switches_silenciosos(exe):
    """
    Modificadors silenciosos correctes per a cada instal.lador.

    No en tenen un de comu: DXSETUP vol /silent i peta amb /q ("Modificador
    de la linea de comandos no valido"), els vc_redist moderns volen
    /install /quiet /norestart, i els antics /q /norestart.
    """
    nom = os.path.basename(exe).lower()
    if "dxsetup" in nom:
        return ["/silent"]
    if "vc_redist" in nom:
        return ["/install", "/quiet", "/norestart"]
    if "vcredist" in nom:
        return ["/q", "/norestart"]
    if "dotnet" in nom or nom.startswith("ndp"):
        return ["/q", "/norestart"]
    if "oalinst" in nom:
        return ["/silent"]
    if "physx" in nom:
        return ["/s"]
    if "prereqsetup" in nom:
        return ["/quiet"]
    if "xnafx" in nom:
        return ["/q"]
    return ["/q", "/norestart"]

def run_pending_redistributables():
    """
    Instal.la els prerequisits dels jocs (Visual C++, DirectX, .NET).

    Metode principal: steamservice.exe /installscript. Es el mecanisme intern
    del propi Steam, i te dos avantatges sobre executar els .exe a ma:
      1. Steam ja sap els modificadors correctes de cada instal.lador.
      2. Escriu la marca 'hasrunkey' al registre, que es el que fa que Steam
         DEIXI de rellancar-los. Executant els .exe pel nostre compte
         s'instal.larien, pero Steam els tornaria a llancar igualment.
    Si no hi ha installscript.vdf, executem l'exe amb els seus modificadors.
    """
    steam_dir = get_steam_install_dir()
    if not steam_dir:
        print("[AVIS] Steam no trobat.")
        return

    biblioteques = [os.path.join(steam_dir, "steamapps")]
    vdf = os.path.join(steam_dir, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf):
        try:
            with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                for ruta in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                    biblioteques.append(
                        os.path.join(ruta.replace("\\\\", "\\"), "steamapps")
                    )
        except Exception:
            pass

    steamservice = os.path.join(steam_dir, "bin", "steamservice.exe")
    te_servei = os.path.exists(steamservice)
    if te_servei:
        print(f"    Fent servir: {steamservice}")
    else:
        print("    [AVIS] steamservice.exe no trobat; executant els .exe")
        print("           directament (no quedara marcat com a fet).")

    mapa = _steam_appid_map(biblioteques)
    fets = errors = 0

    for lib in biblioteques:
        common = os.path.join(lib, "common")
        if not os.path.isdir(common):
            continue
        for arrel, _, fitxers in os.walk(common):
            if "_commonredist" not in arrel.lower():
                continue

            # Deduir l'appid a partir de la carpeta del joc
            rel = os.path.relpath(arrel, common).split(os.sep)[0]
            appid = mapa.get(rel.lower(), "0")

            if te_servei and "installscript.vdf" in [f.lower() for f in fitxers]:
                script = os.path.join(arrel, "installscript.vdf")
                print(f"    [script] {rel}: {os.path.relpath(script, common)}")
                try:
                    r = subprocess.run(
                        [steamservice, "/installscript", script, appid],
                        capture_output=True, timeout=600
                    )
                    if r.returncode == 0:
                        fets += 1
                    else:
                        print(f"        (codi {r.returncode})")
                        errors += 1
                except subprocess.TimeoutExpired:
                    print("        (temps esgotat)")
                    errors += 1
                except Exception as e:
                    print(f"        (error: {e})")
                    errors += 1
                continue

            for fitxer in fitxers:
                if not fitxer.lower().endswith(".exe"):
                    continue
                exe = os.path.join(arrel, fitxer)
                args = _switches_silenciosos(exe)
                print(f"    [exe] {fitxer} {' '.join(args)}")
                try:
                    r = subprocess.run([exe] + args, capture_output=True,
                                       timeout=600)
                    if r.returncode in (0, 1638, 3010):  # ok / ja instal.lat / cal reiniciar
                        fets += 1
                    else:
                        print(f"        (codi {r.returncode})")
                        errors += 1
                except subprocess.TimeoutExpired:
                    print("        (temps esgotat: probablement ha obert una")
                    print("         finestra. Tanca-la si encara hi es.)")
                    errors += 1
                except Exception as e:
                    print(f"        (error: {e})")
                    errors += 1

    print(f"\n[OK] {fets} prerequisits processats, {errors} amb problemes.")
    if fets == 0 and errors == 0:
        print("     No s'ha trobat cap _CommonRedist.")

# ===================================================================
# 3. LÒGICA D'UTILITAT I REGISTRE
# ===================================================================

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def load_disks_cache():
    """
    Combina la cache compartida (instal.lada per l'admin, nomes lectura) amb
    la cache propia de l'usuari. La de l'usuari te prioritat.
    """
    dades = load_json(SHARED_DISKS_FILE)
    dades.update(load_json(FLOPPY_DISKS_FILE))
    return dades

def save_json(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Error al guardar '{file_path}': {e}")

def get_galaxy_path():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, 
            r"SOFTWARE\GOG.com\GalaxyClient\paths", 
            0, 
            winreg.KEY_READ | winreg.KEY_WOW64_32KEY
        )
        path, _ = winreg.QueryValueEx(key, "client")
        winreg.CloseKey(key)
        exe_path = os.path.join(path, "GalaxyClient.exe")
        if os.path.exists(exe_path):
            return exe_path
    except OSError:
        pass
    return None

def _read_reg_value(hive, subkey, value_name, flags=winreg.KEY_READ):
    try:
        key = winreg.OpenKey(hive, subkey, 0, flags)
        data, _ = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return data
    except OSError:
        return None

def _is_rejected_scummvm(path):
    """
    Descarta ScummVM que no siguin la versio oficial baixada per l'usuari:
    els que venen incrustats amb jocs de GOG viuen dins la carpeta del joc.
    """
    low = os.path.normpath(path).lower()
    for marcador in ["gog games", "gog.com", "gog galaxy", "\\steamapps\\",
                     "steamlibrary", "\\games\\"]:
        if marcador in low:
            return True
    return False

def get_scummvm_path():
    """
    Retorna NOMES el ScummVM oficial instal.lat per l'usuari des de scummvm.org.

    L'instal.lador oficial es Inno Setup i registra la clau de desinstal.lacio
    'ScummVM_is1' (el sufix _is1 es la signatura d'Inno Setup). Ni el ScummVM
    que GOG incrusta dins les carpetes dels jocs ni les versions portables
    creen aquesta clau, aixi que es el discriminador fiable.
    """
    uninstall_base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"

    # Totes les vistes on Inno Setup pot haver escrit la clau:
    # HKCU  -> instal.lacio "nomes per a mi" (sense admin)
    # HKLM  -> instal.lacio per a tots els usuaris (vista 64 i 32 bits)
    vistes = [
        (winreg.HKEY_CURRENT_USER,  winreg.KEY_READ),
        (winreg.HKEY_CURRENT_USER,  winreg.KEY_READ | winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_32KEY),
    ]

    candidats = []

    for hive, flags in vistes:
        subkey = f"{uninstall_base}\\ScummVM_is1"

        # InstallLocation es el valor estandard d'Inno Setup (amb barra final)
        loc = _read_reg_value(hive, subkey, "InstallLocation", flags)
        if loc:
            candidats.append(os.path.join(os.path.normpath(loc), "scummvm.exe"))

        # DisplayIcon sol apuntar directament a l'executable
        icon = _read_reg_value(hive, subkey, "DisplayIcon", flags)
        if icon:
            candidats.append(os.path.normpath(icon.split(",")[0].strip('"')))

        # UninstallString apunta a unins000.exe -> la carpeta d'instal.lacio
        unins = _read_reg_value(hive, subkey, "UninstallString", flags)
        if unins:
            carpeta = os.path.dirname(unins.strip('"'))
            if carpeta:
                candidats.append(os.path.join(carpeta, "scummvm.exe"))

    for exe in candidats:
        if exe.lower().endswith("scummvm.exe") and os.path.exists(exe):
            if not _is_rejected_scummvm(exe):
                return exe

    # Fallback: rutes per defecte de l'instal.lador oficial, per si la clau
    # de registre s'ha perdut pero el programa hi segueix sent.
    for p in [
        r"C:\Program Files\ScummVM\scummvm.exe",
        r"C:\Program Files (x86)\ScummVM\scummvm.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\ScummVM\scummvm.exe"),
    ]:
        if os.path.exists(p) and not _is_rejected_scummvm(p):
            return p

    return None

def get_scummvm_config_path():
    """
    Localitza el scummvm.ini de L'USUARI ACTUAL.

    La llista de jocs de ScummVM NO viu al costat de l'executable: viu a
    %APPDATA%\\ScummVM\\scummvm.ini i es PER USUARI. Si el servei corre sota
    un compte diferent del que ha configurat els jocs, s'obrira el ScummVM
    correcte pero amb la biblioteca buida.
    """
    candidats = [
        os.path.join(os.getenv("APPDATA", ""), "ScummVM", "scummvm.ini"),
        os.path.join(os.getenv("APPDATA", ""), "scummvm.ini"),
    ]
    exe = get_scummvm_path()
    if exe:  # instal.lacions portables el guarden al costat de l'exe
        candidats.append(os.path.join(os.path.dirname(exe), "scummvm.ini"))

    for c in candidats:
        if c and os.path.exists(c):
            return c
    return None

def get_scummvm_targets(ini_path=None):
    """Retorna els IDs de joc (targets) configurats al scummvm.ini."""
    ini_path = ini_path or get_scummvm_config_path()
    if not ini_path or not os.path.exists(ini_path):
        return []

    reservades = {"scummvm", "cloud", "keymapper", "onscreen_control"}
    targets = []
    try:
        with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
            for linia in f:
                linia = linia.strip()
                if linia.startswith("[") and linia.endswith("]"):
                    nom = linia[1:-1].strip()
                    if nom.lower() not in reservades:
                        targets.append(nom)
    except Exception:
        pass
    return targets

def is_gog_installed(gog_game_id):
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, 
            f"SOFTWARE\\GOG.com\\Games\\{gog_game_id}", 
            0, 
            winreg.KEY_READ | winreg.KEY_WOW64_32KEY
        )
        winreg.CloseKey(key)
        return True
    except OSError:
        return False

def get_steam_install_dir():
    """Carpeta base de Steam (no l'executable)."""
    for hive, flags in [
        (winreg.HKEY_CURRENT_USER, winreg.KEY_READ),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_32KEY),
    ]:
        for value in ["SteamPath", "InstallPath"]:
            p = _read_reg_value(hive, r"SOFTWARE\Valve\Steam", value, flags)
            if p and os.path.isdir(p):
                return os.path.normpath(p)
    for p in [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]:
        if os.path.isdir(p):
            return p
    return None

def is_steam_installed(steam_app_id):
    """
    Comprova si un joc de Steam ja esta instal.lat.

    Fa servir dos metodes perque el registre HKCU pot no ser accessible si el
    servei s'ha elevat amb un compte d'administrador diferent: primer el
    registre, i despres els fitxers appmanifest_<id>.acf de totes les
    biblioteques de Steam (metode independent de l'usuari).
    """
    app_id = str(steam_app_id)

    # Metode 1: registre de l'usuari
    installed = _read_reg_value(
        winreg.HKEY_CURRENT_USER,
        f"SOFTWARE\\Valve\\Steam\\Apps\\{app_id}",
        "Installed"
    )
    if installed == 1:
        return True

    # Metode 2: buscar appmanifest_<id>.acf a totes les biblioteques
    steam_dir = get_steam_install_dir()
    if not steam_dir:
        return False

    biblioteques = [os.path.join(steam_dir, "steamapps")]
    vdf = os.path.join(steam_dir, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf):
        try:
            with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                for ruta in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                    biblioteques.append(
                        os.path.join(ruta.replace("\\\\", "\\"), "steamapps")
                    )
        except Exception:
            pass

    for lib in biblioteques:
        if os.path.exists(os.path.join(lib, f"appmanifest_{app_id}.acf")):
            return True

    return False

# ===================================================================
# 4. APIs I LLANÇADORS (GOG/STEAM/SCUMM/MINECRAFT/EA)
# ===================================================================

def get_name_from_gog(gog_id):
    url = f"https://api.gog.com/products/{gog_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('title')
    except Exception: pass
    return None

def get_name_from_steam(steam_id):
    url = f"https://store.steampowered.com/api/appdetails?appids={steam_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if str(steam_id) in data and data[str(steam_id)].get('success'):
                    return data[str(steam_id)]['data'].get('name')
    except Exception: pass
    return None

def handle_gog_game(game_name, gog_game_id):
    galaxy_exe = get_galaxy_path()
    print(f"[PLATFORM: GOG] '{game_name}' (ID: {gog_game_id})")
    if is_gog_installed(gog_game_id):
        if galaxy_exe:
            subprocess.Popen([galaxy_exe, "/command=runGame", f"/gameId={gog_game_id}"])
        else:
            launch_uri_as_user(f"goggalaxy://runGame/{gog_game_id}")
    else:
        launch_uri_as_user(f"goggalaxy://installGame/{gog_game_id}")

def launch_uri_as_user(uri):
    """
    Llanca un URI de protocol (steam://, goggalaxy://...) DE-ELEVAT.

    Per que cal: quan el servei corre com a proces elevat (admin), les crides
    os.startfile() i 'cmd /c start' hereten el token elevat. Els protocols com
    steam:// estan registrats a HKEY_CURRENT_USER de l'usuari normal, i un
    proces d'alta integritat no els pot resoldre -> el llancament falla en
    silenci. explorer.exe sempre corre a integritat mitjana com a l'usuari de
    la sessio, aixi que li passem l'URI i ell el resol correctament.
    """
    subprocess.Popen(["explorer.exe", uri])

def handle_steam_game(game_name, steam_app_id):
    app_id = str(steam_app_id)

    if not get_steam_install_dir():
        print(f"[AVIS] Steam no sembla instal.lat en aquest equip.")
        print(f"       S'intenta el protocol igualment (AppID: {app_id})")

    if is_steam_installed(app_id):
        uri = f"steam://rungameid/{app_id}"
        print(f"[PLATFORM: STEAM] Executant '{game_name}' (AppID: {app_id})")
    else:
        uri = f"steam://install/{app_id}"
        print(f"[PLATFORM: STEAM] '{game_name}' no instal.lat -> instal.lador (AppID: {app_id})")

    print(f"    URI: {uri}")
    try:
        launch_uri_as_user(uri)
    except Exception as e:
        print(f"[ERROR] No s'ha pogut llancar l'URI de Steam: {e}")

def handle_scummvm_game_direct(raw_text):
    scumm_exe = get_scummvm_path()
    if not scumm_exe:
        print("[ERROR] No s'ha trobat cap ScummVM oficial instal.lat.")
        print("        Descarrega'l de https://www.scummvm.org/downloads/")
        return

    scumm_id = raw_text.upper().split("SCUMM:")[-1].strip().lower()
    if not scumm_id:
        return

    ini = get_scummvm_config_path()
    targets = get_scummvm_targets(ini)

    print(f"[PLATFORM: SCUMMVM] Usuari    : {os.getenv('USERNAME')}")
    print(f"[PLATFORM: SCUMMVM] Executable: {scumm_exe}")
    print(f"[PLATFORM: SCUMMVM] Config    : {ini or 'NO TROBAT'}")
    print(f"[PLATFORM: SCUMMVM] Jocs configurats: {len(targets)}")

    # La biblioteca de ScummVM es per usuari. Si el servei corre sota un
    # compte diferent del que ha configurat els jocs, s'obrira la finestra
    # buida. Val mes dir-ho que no pas obrir una finestra sense explicacio.
    if targets and scumm_id not in [t.lower() for t in targets]:
        print(f"[AVIS] El target '{scumm_id}' NO esta al scummvm.ini d'aquest usuari.")
        print(f"       Disponibles: {', '.join(targets[:15])}")
        print(f"       Si aquest no es l'usuari que va afegir els jocs, el servei")
        print(f"       esta corrent amb el compte equivocat (mira el log inicial).")
    elif not targets:
        print(f"[AVIS] El scummvm.ini d'aquest usuari no te cap joc configurat.")
        print(f"       Afegeix-los des de ScummVM, o comprova que el servei corre")
        print(f"       amb l'usuari correcte (mira el log inicial).")

    print(f"[PLATFORM: SCUMMVM] Launching ID: '{scumm_id}'")
    subprocess.Popen([scumm_exe, scumm_id])

def run_diagnostics():
    """Mostra que detecta el script. Executa amb: python nfc_launcher.py --diag"""
    print("=" * 70)
    print(f" NFC Game Launcher - Diagnostic (v{APP_VERSION})")
    print("=" * 70)
    print(f"Executant com a admin : {bool(is_admin())}")
    print(f"Usuari del proces     : {os.getenv('USERNAME')}")
    print(f"Perfil (APPDATA)      : {os.getenv('APPDATA')}")
    print(f"Interpret Python      : {sys.executable}")
    print(f"Carpeta instal.lacio  : {INSTALL_DIR}")
    print(f"Dades (log/cache)     : {USER_DATA_DIR}")
    print()
    check_old_install()
    scumm = get_scummvm_path()
    ini = get_scummvm_config_path()
    targets = get_scummvm_targets(ini)
    print(f"ScummVM (oficial)     : {scumm or 'NO TROBAT'}")
    print(f"ScummVM config (ini)  : {ini or 'NO TROBAT'}")
    print(f"ScummVM jocs config.  : {len(targets)}")
    if targets:
        for t in targets[:20]:
            print(f"    - {t}")
    else:
        print("    (cap joc: o be no n'hi ha, o el servei corre amb un altre usuari)")
    print()
    print(f"Steam (carpeta)       : {get_steam_install_dir() or 'NO TROBAT'}")
    print(f"Steam obert ara       : {is_steam_running()}")
    steam_dir = get_steam_install_dir()
    if steam_dir:
        vdf = os.path.join(steam_dir, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            try:
                with open(vdf, "r", encoding="utf-8", errors="ignore") as f:
                    rutes = re.findall(r'"path"\s+"([^"]+)"', f.read())
                print("Biblioteques de Steam :")
                for r in rutes:
                    print(f"    - {r.replace(chr(92)+chr(92), chr(92))}")
            except Exception as e:
                print(f"    (error llegint el vdf: {e})")
    print(f"GOG Galaxy            : {get_galaxy_path() or 'NO TROBAT'}")
    print()
    print("--- Causes d'UAC en obrir un joc per primer cop ---")
    estat = get_steam_service_state()
    print(f"Steam Client Service  : {estat}")
    if estat != "RUNNING":
        print("    [!] Aquest servei es el que instal.la els prerequisits SENSE")
        print("        demanar UAC. Si no corre, cada joc nou demanara password.")
        print("        Solucio: sc config 'Steam Client Service' start= demand")
    desajust = check_commonredist_registry()
    print(f"Claus CommonRedist    : {desajust}")
    print()
    print("Prova d'ID de Steam (deixa buit per ometre):")
    test_id = input("  AppID: ").strip()
    if test_id:
        print(f"  Instal.lat? {is_steam_installed(test_id)}")
        print(f"  Nom oficial: {get_name_from_steam(test_id) or 'desconegut'}")
    print("=" * 70)
    input("Prem Enter per sortir...")
    sys.exit(0)

def handle_minecraft():
        print(T("mc_init"))
        try:
            # 1. Obri el Minecraft Launcher de la Store/Xbox via Protocol Directe (El mètode més fiable)
            try:
                os.startfile(r"shell:AppsFolder\Microsoft.4297127926808_8wekyb3d8bbwe!MinecraftLauncher")
                print(T("mc_launched_store"))
                return
            except Exception:
                pass

            # 2. Cercar l'executable del llançador clàssic (Win32 / Java antic)
            rutes_exe = [
                r"C:\Program Files (x86)\Minecraft Launcher\MinecraftLauncher.exe",
                r"C:\Program Files\Minecraft Launcher\MinecraftLauncher.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Minecraft Launcher\MinecraftLauncher.exe")
            ]
            for ruta in rutes_exe:
                if os.path.exists(ruta):
                    print(f'{T("mc_classic")}{ruta}')
                    os.startfile(ruta)
                    return

            # 3. Si no troba el llançador, obrir el joc directament (Bedrock)
            try:
                launch_uri_as_user("minecraft:")
                print(T("mc_uri"))
                return
            except Exception:
                pass

            # 4. Fallback: Obrir la Store per descarregar el Launcher
            print(T("mc_store"))
            launch_uri_as_user("ms-windows-store://pdp/?productid=9PGW18NPBZJJ")

        except Exception as e:
            print(f'{T("mc_err")}{e}')

def handle_ea_game(raw_text):
    ea_ids = raw_text.upper().split("EA:")[-1].strip()
    if ea_ids:
        print(f"[PLATFORM: EA APP] Llancant els IDs: '{ea_ids}'")
        try:
            launch_uri_as_user(f"origin2://game/launch/?offerIds={ea_ids}")
        except Exception as e:
            print(f"[ERROR] Executant joc d'EA: {e}")

def process_game_by_platform(app_id, platform):
    """
    Llanca el joc SEMPRE, encara que no se'n pugui resoldre el nom.

    IMPORTANT: el llancament NO pot dependre de cap crida de xarxa. L'API de
    Steam retorna success:false per molts AppIDs (DLC, jocs delistats,
    restriccions regionals) i esta limitada a ~200 peticions/5 min. Abans, si
    la consulta fallava el joc no s'executava i no es deia res. Per llancar
    nomes cal l'ID i la plataforma, que ja els tenim de la targeta NFC.
    """
    floppy_disks = load_disks_cache()
    registry_key = f"{platform.upper()}:{app_id}"

    # 1. Nom des de la cache local, si hi es (sense xarxa)
    name = None
    if registry_key in floppy_disks:
        name = floppy_disks[registry_key].get("name")
    elif platform == "gog":
        name = load_json(GOG_CATALOG_FILE).get(app_id)

    # 2. LLANCAR JA, amb el nom que tinguem (o sense)
    etiqueta = name or f"AppID {app_id}"
    if platform == "steam":
        handle_steam_game(etiqueta, app_id)
    else:
        handle_gog_game(etiqueta, app_id)

    # 3. Nomes despres de llancar, mirar d'enriquir la cache. Si falla, tant se val.
    if not name:
        try:
            oficial = (get_name_from_steam(app_id) if platform == "steam"
                       else get_name_from_gog(app_id))
            if oficial:
                floppy_disks[registry_key] = {
                    "name": oficial, "id": app_id, "platform": platform
                }
                save_json(FLOPPY_DISKS_FILE, floppy_disks)
                print(f"    (nom resolt i desat: '{oficial}')")
            else:
                print(f"    (avis: l'API no ha identificat l'AppID {app_id}; "
                      f"llancat igualment)")
        except Exception as e:
            print(f"    (avis: no s'ha pogut resoldre el nom: {e})")

def auto_discover_platform(app_id):
    """
    Targeta amb un numero sense prefix de plataforma. Aqui SI cal la xarxa per
    endevinar la plataforma, pero si tot falla avisem en comptes de callar.
    """
    if get_name_from_gog(app_id):
        return process_game_by_platform(app_id, "gog")
    if get_name_from_steam(app_id):
        return process_game_by_platform(app_id, "steam")

    print(f"[AVIS] No s'ha pogut determinar la plataforma de l'ID '{app_id}'.")
    print(f"       Sense connexio o ID desconegut. Escriu la targeta amb el")
    print(f"       prefix explicit ('STEAM:{app_id}' o 'GOG:{app_id}').")

def process_nfc_input(raw_text):
    clean_text = raw_text.upper().strip()
    
    if "MINECRAFT" in clean_text:
        return handle_minecraft()
    
    if "SCUMM:" in clean_text:
        return handle_scummvm_game_direct(raw_text)

    if "EA:" in clean_text:
        return handle_ea_game(raw_text)

    match = re.search(r'\d+', clean_text)
    if "STEAM:" in clean_text and match:
        return process_game_by_platform(match.group(0), "steam")
    
    if "GOG:" in clean_text and match:
        return process_game_by_platform(match.group(0), "gog")

    if match:
        return auto_discover_platform(match.group(0))

# ===================================================================
# 5. LECTOR NFC
# ===================================================================

class NFCGameMonitor(CardObserver):
    def update(self, observable, actions):
        (addedcards, removedcards) = actions
        for card in addedcards:
            try:
                connection = card.createConnection()
                connection.connect()
                
                data_part1, sw1_1, sw2_1 = connection.transmit([0xFF, 0xB0, 0x00, 0x04, 0x10])
                data_part2, sw1_2, sw2_2 = connection.transmit([0xFF, 0xB0, 0x00, 0x08, 0x10])
                
                if sw1_1 == 0x90 and sw2_1 == 0x00:
                    raw_bytes = bytes(data_part1)
                    if sw1_2 == 0x90 and sw2_2 == 0x00:
                        raw_bytes += bytes(data_part2)
                        
                    raw_text = "".join([chr(b) for b in raw_bytes if 32 <= b <= 126]).strip()
                    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] NFC DETECTED: '{raw_text}'")
                    sys.stdout.flush()
                    process_nfc_input(raw_text)
            except Exception as e:
                print(f"[ERROR] Lectura NFC: {e}")
                sys.stdout.flush()

# ===================================================================
# 6. PUNT D'ENTRADA (MAIN)
# ===================================================================

if __name__ == "__main__":
    if "--diag" in sys.argv:
        run_diagnostics()

    if "--prep" in sys.argv or "--fix-redist" in sys.argv:
        # Deixa els jocs acabats d'instal.lar llestos perque l'usuari estandard
        # els pugui obrir sense que salti l'UAC la primera vegada.
        elevate_privileges()
        print("=" * 70)
        print(f" Preparant jocs de Steam (v{APP_VERSION})")
        print("=" * 70)

        print(f"\n[1/3] Steam Client Service: {get_steam_service_state()}")
        if get_steam_service_state() != "RUNNING":
            print("      Intentant habilitar-lo...")
            try:
                subprocess.run(["sc", "config", "Steam Client Service",
                                "start=", "demand"], capture_output=True)
                subprocess.run(["sc", "start", "Steam Client Service"],
                               capture_output=True)
                print(f"      Ara: {get_steam_service_state()}")
            except Exception as e:
                print(f"      No s'ha pogut: {e}")

        print(f"\n[2/3] Claus CommonRedist: {check_commonredist_registry()}")
        fix_commonredist_registry()
        despres = check_commonredist_registry()
        print(f"      Despres de reparar: {despres}")
        if "DESAJUST" in despres:
            print("      [!] La reparacio NO ha funcionat. Comprova que aquesta")
            print("          finestra corre realment com a administrador.")
        else:
            print("      [OK] Desajust corregit.")

        print("\n[3/3] Prerequisits pendents (Visual C++, DirectX, .NET)...")
        run_pending_redistributables()

        print("\nFet. Prova d'obrir un joc amb l'usuari estandard.")
        input("\nPrem Enter per sortir...")
        sys.exit(0)

    is_background = "--background" in sys.argv or sys.executable.lower().endswith("pythonw.exe")
    is_installed = os.path.abspath(__file__).lower() == INSTALL_FILE.lower()

    if is_background:
        # Si aixo peta (usuari sense permisos d'escriptura), sota pythonw el
        # servei moriria sense deixar cap rastre. Amb fallback a TEMP.
        try:
            log_handle = open(LOG_FILE, "a", encoding="utf-8")
        except Exception:
            try:
                fallback = os.path.join(os.getenv("TEMP", "."), "nfc_launcher.log")
                log_handle = open(fallback, "a", encoding="utf-8")
            except Exception:
                log_handle = open(os.devnull, "w")

        sys.stdout = log_handle
        sys.stderr = log_handle

        print(f"\n--- Iniciant Servei NFC v{APP_VERSION} ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
        print(f"    Usuari: {os.getenv('USERNAME')} | Elevat: {bool(is_admin())}")
        print(f"    APPDATA: {os.getenv('APPDATA')}")
        print(f"    Dades usuari: {USER_DATA_DIR}")
        print(f"    ScummVM: {get_scummvm_path() or 'no trobat'}")
        print(f"    ScummVM ini: {get_scummvm_config_path() or 'no trobat'} "
              f"({len(get_scummvm_targets())} jocs)")
        print(f"    Steam:   {get_steam_install_dir() or 'no trobat'}")
        if is_admin():
            print(f"    {T('service_elevated_warn')}")
        
        cardmonitor = CardMonitor()
        observer = NFCGameMonitor()
        cardmonitor.addObserver(observer)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            cardmonitor.removeObserver(observer)
            log_handle.close()
            
    else:
        if not is_installed and "--lang" not in sys.argv:
            print("Select language / Selecciona l'idioma:")
            print("1. English")
            print("2. Català")
            while True:
                choice = input("Option [1/2]: ").strip()
                if choice == '1':
                    lang = 'en'
                    break
                elif choice == '2':
                    lang = 'ca'
                    break

        if is_already_installed():
            pids = find_service_pids()
            print("\n" + "=" * 70)
            print(T('already_installed'))
            print("=" * 70)
            print(f"  {T('ai_folder')} {INSTALL_DIR}")
            print(f"  {T('ai_autostart')} "
                  f"{'OK' if os.path.exists(get_autostart_path()) else 'NO'}")
            print(f"  {T('ai_service')} "
                  f"{('EN MARXA (PID ' + ', '.join(map(str, pids)) + ')') if pids else 'ATURAT'}")
            print()
            print(f"  1. {T('opt_uninstall')}")
            print(f"  2. {T('opt_reinstall')}")
            print(f"  3. {T('opt_exit')}")
            while True:
                opcio = input(f"\n{T('opt_prompt')} ").strip()
                if opcio == "1":
                    uninstall_from_system()
                elif opcio == "2":
                    print(f"\n{T('reinstalling')}")
                    stop_service()
                    install_to_system()
                elif opcio == "3":
                    sys.exit(0)
        else:
            install_to_system()
