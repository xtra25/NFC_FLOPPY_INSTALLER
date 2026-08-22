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
# CONFIGURACIÓ DE RUTES D'INSTAL·LACIÓ
# ===================================================================
INSTALL_DIR = r"C:\NFC_Launcher"
INSTALL_FILE = os.path.join(INSTALL_DIR, "nfc_launcher.py")
LOG_FILE = os.path.join(INSTALL_DIR, "nfc_launcher.log")
GAME_DIR_DEFAULT = r"C:\FloppyGames"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLOPPY_DISKS_FILE = os.path.join(BASE_DIR, "floppy_disks.json")
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
    """Reinicia el propi script sol·licitant elevació UAC a Windows."""
    if not is_admin():
        print("[INFO] Es requereixen permisos d'administrador per instal·lar. Sol·licitant-los...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1
        )
        sys.exit(0)

def check_and_install_dependencies():
    try:
        import smartcard
    except ImportError:
        print("[STARTUP] Missing 'pyscard'. Instal·lant...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyscard"])
            importlib.invalidate_caches()
            print("[STARTUP] 'pyscard' instal·lat.\n")
        except subprocess.CalledProcessError as e:
            print(f"[CRITICAL ERROR] Error al instal·lar dependències: {e}")
            input("Prem Enter per sortir...")
            sys.exit(1)

check_and_install_dependencies()
from smartcard.CardMonitoring import CardMonitor, CardObserver

# ===================================================================
# 2. INSTAL·LACIÓ I CONFIGURACIÓ
# ===================================================================

def install_to_system():
    """Copia l'script al directori permanent i prepara l'entorn."""
    elevate_privileges() # Assegura que som Admin abans de fer res
    
    print("\n" + "=" * 70)
    print(" [INSTALL] Iniciant instal·lació al sistema...")
    print("=" * 70)

    # Preguntar per la carpeta de jocs personalitzada
    global GAME_DIR_DEFAULT
    print(f"\nRuta per defecte per als jocs: {GAME_DIR_DEFAULT}")
    custom_path = input("Escriu una ruta nova (o prem Enter per mantenir la per defecte): ").strip()
    if custom_path:
        GAME_DIR_DEFAULT = os.path.normpath(custom_path)
        print(f" -> S'utilitzarà la ruta personalitzada: {GAME_DIR_DEFAULT}")

    # 1. Crear directori d'instal·lació
    os.makedirs(INSTALL_DIR, exist_ok=True)

    # 2. Copiar l'script actual al nou directori
    current_file = os.path.abspath(__file__)
    if current_file.lower() != INSTALL_FILE.lower():
        shutil.copy2(current_file, INSTALL_FILE)
        print(f" -> Còpia de l'script a: {INSTALL_FILE}")

        # Copiar JSONs si existeixen al lloc original
        for json_file in ["floppy_disks.json", "gog_catalog_full.json"]:
            src_json = os.path.join(BASE_DIR, json_file)
            if os.path.exists(src_json):
                shutil.copy2(src_json, os.path.join(INSTALL_DIR, json_file))
                print(f" -> Còpia de la base de dades: {json_file}")

    # 3. Permisos de la carpeta de jocs
    setup_game_folder_permissions()

    # 4. Auto-arrencada a Windows
    setup_windows_autostart(INSTALL_FILE)

    # 5. Iniciar el servei en segon pla immediatament des de la ruta instal·lada
    pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable # Fallback

    subprocess.Popen([pythonw_exe, INSTALL_FILE, "--background"])

    print("\n" + "=" * 70)
    print(" [SUCCESS] Instal·lació completada amb èxit!")
    print(f" [INFO] El servei ja corre en segon pla. L'arxiu log està a {LOG_FILE}")
    print(f"\n >>> JA POTS ESBORRAR AQUEST FITXER ORIGINAL: {current_file}")
    print("=" * 70)
    
    input("\nPrem Enter per tancar aquesta finestra...")
    sys.exit(0)

def setup_windows_autostart(target_script):
    try:
        startup_folder = os.path.join(
            os.getenv('ALLUSERSPROFILE'), 
            r'Microsoft\Windows\Start Menu\Programs\StartUp'
        )
        launcher_file = os.path.join(startup_folder, "NFC_Floppy_AutoStart.bat")
        pythonw_exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        
        bat_content = f'@echo off\nstart "" "{pythonw_exe}" "{target_script}" --background\n'
        
        with open(launcher_file, "w", encoding="utf-8") as f:
            f.write(bat_content)
        print(" -> Auto-arrencada global configurada correctament.")
    except Exception as e:
        print(f"[WARNING] No s'ha pogut configurar l'auto-arrencada: {e}")

def setup_game_folder_permissions():
    target_path = os.path.normpath(GAME_DIR_DEFAULT)
    try:
        os.makedirs(target_path, exist_ok=True)
        cmd_grant = f'icacls "{target_path}" /grant *S-1-5-32-545:(OI)(CI)F /T /q'
        subprocess.run(cmd_grant, shell=True, check=True)
        print(f" -> Permisos de control total concedits a: '{target_path}'")

        steam_dir = r"C:\Program Files (x86)\Steam"
        if os.path.exists(steam_dir):
            cmd_steam = f'icacls "{steam_dir}" /grant *S-1-5-32-545:(OI)(CI)M /T /q'
            subprocess.run(cmd_steam, shell=True, check=True)
            print(" -> Permisos ajustats a Steam per evitar problemes d'UAC.")

    except subprocess.CalledProcessError as code:
        print(f"[ERROR CRÍTIC] Falla a l'assignar permisos amb icacls. Codi d'error: {code.returncode}")

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

def get_scummvm_path():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, 
            r"SOFTWARE\ScummVM\ScummVM", 
            0, 
            winreg.KEY_READ | winreg.KEY_WOW64_32KEY
        )
        path, _ = winreg.QueryValueEx(key, "")
        winreg.CloseKey(key)
        exe = os.path.join(path, "scummvm.exe")
        if os.path.exists(exe):
            return exe
    except OSError:
        pass
    
    for p in [r"C:\Program Files\ScummVM\scummvm.exe", r"C:\Program Files (x86)\ScummVM\scummvm.exe"]:
        if os.path.exists(p): return p
    return None

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

def is_steam_installed(steam_app_id):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"SOFTWARE\\Valve\\Steam\\Apps\\{steam_app_id}", 0, winreg.KEY_READ)
        installed, _ = winreg.QueryValueEx(key, "Installed")
        winreg.CloseKey(key)
        return installed == 1
    except OSError:
        return False

# ===================================================================
# 4. APIs I LLANÇADORS (GOG/STEAM/SCUMM)
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
            os.startfile(f"goggalaxy://runGame/{gog_game_id}")
    else:
        os.startfile(f"goggalaxy://installGame/{gog_game_id}")

def handle_steam_game(game_name, steam_app_id):
    print(f"[PLATFORM: STEAM] '{game_name}' (AppID: {steam_app_id})")
    os.startfile(f"steam://rungameid/{steam_app_id}")

def handle_scummvm_game_direct(raw_text):
    scumm_exe = get_scummvm_path()
    if not scumm_exe: return
    scumm_id = raw_text.upper().split("SCUMM:")[-1].strip().lower()
    if scumm_id:
        print(f"[PLATFORM: SCUMMVM] Launching ID: '{scumm_id}'")
        subprocess.Popen([scumm_exe, scumm_id])

def process_game_by_platform(app_id, platform):
    floppy_disks = load_json(FLOPPY_DISKS_FILE)
    registry_key = f"{platform.upper()}:{app_id}"

    if registry_key in floppy_disks:
        info = floppy_disks[registry_key]
        name = info.get("name", "Unknown")
        if platform == "steam": handle_steam_game(name, app_id)
        else: handle_gog_game(name, app_id)
        return

    official_name = get_name_from_steam(app_id) if platform == "steam" else get_name_from_gog(app_id)
    if not official_name and platform == "gog":
        official_name = load_json(GOG_CATALOG_FILE).get(app_id)

    if official_name:
        floppy_disks[registry_key] = {"name": official_name, "id": app_id, "platform": platform}
        save_json(FLOPPY_DISKS_FILE, floppy_disks)
        
        if platform == "steam": handle_steam_game(official_name, app_id)
        else: handle_gog_game(official_name, app_id)

def auto_discover_platform(app_id):
    if get_name_from_gog(app_id): return process_game_by_platform(app_id, "gog")
    if get_name_from_steam(app_id): return process_game_by_platform(app_id, "steam")

def process_nfc_input(raw_text):
    clean_text = raw_text.upper().strip()
    
    if "SCUMM:" in clean_text:
        return handle_scummvm_game_direct(raw_text)

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
    is_background = "--background" in sys.argv or sys.executable.lower().endswith("pythonw.exe")
    is_installed = os.path.abspath(__file__).lower() == INSTALL_FILE.lower()

    if is_background:
        log_handle = open(LOG_FILE, "a", encoding="utf-8")
        sys.stdout = log_handle
        sys.stderr = log_handle
        
        print(f"\n--- Iniciant Servei NFC ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
        
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
        if not is_installed:
            install_to_system()
        else:
            print("[INFO] Aquest script normalment s'executa automàticament en segon pla.")
            input("Prem Enter per tancar-lo manualment...")