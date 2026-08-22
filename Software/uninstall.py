import os
import sys
import subprocess
import shutil
import ctypes

INSTALL_DIR = r"C:\NFC_Launcher"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_privileges():
    """Sol·licita elevació UAC per poder esborrar arxius de sistema."""
    if not is_admin():
        print("[INFO] Es requereixen permisos d'administrador per desinstal·lar. Sol·licitant-los...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1
        )
        sys.exit(0)

def stop_running_script():
    """Atura específicament el procés de nfc_launcher sense afectar altres pythons."""
    print("[UNINSTALL] Aturant els processos del monitor NFC en segon pla...")
    try:
        # Utilitzem WMIC per tancar NOMÉS el pythonw que estigui executant el nostre script
        cmd = 'wmic process where "name=\'pythonw.exe\' and commandline like \'%nfc_launcher.py%\'" call terminate'
        subprocess.run(
            cmd, 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        print("[UNINSTALL] Processos aturats.")
    except Exception as e:
        print(f"[WARNING] No s'han pogut aturar els processos: {e}")

def remove_autostart_entry():
    """Elimina l'script de l'inici global de Windows."""
    try:
        startup_folder = os.path.join(
            os.getenv('ALLUSERSPROFILE'), 
            r'Microsoft\Windows\Start Menu\Programs\StartUp'
        )
        launcher_file = os.path.join(startup_folder, "NFC_Floppy_AutoStart.bat")

        if os.path.exists(launcher_file):
            os.remove(launcher_file)
            print(f"[UNINSTALL] Arxiu d'auto-arrencada eliminat: '{launcher_file}'")
        else:
            print("[UNINSTALL] No s'ha trobat l'arxiu d'auto-arrencada. S'omet...")
    except Exception as e:
        print(f"[ERROR] Fallada al eliminar l'arxiu d'auto-arrencada: {e}")

def remove_installation_dir():
    """Elimina el directori sencer d'instal·lació, incloent bases de dades i logs."""
    if os.path.exists(INSTALL_DIR):
        choice = input(f"\nVols esborrar tota la carpeta d'instal·lació ({INSTALL_DIR}) incloent els logs i la base de dades? [y/N]: ").strip().lower()
        if choice == 'y':
            try:
                shutil.rmtree(INSTALL_DIR)
                print(f"[UNINSTALL] Directori '{INSTALL_DIR}' esborrat completament.")
            except Exception as e:
                print(f"[ERROR] No s'ha pogut esborrar el directori: {e}")
                print("[INFO] És possible que algun arxiu estigui bloquejat. Pots esborrar la carpeta manualment.")
    else:
        print(f"[UNINSTALL] La carpeta '{INSTALL_DIR}' no existeix. Cap acció necessària.")

if __name__ == "__main__":
    elevate_privileges()
    
    print("=" * 70)
    print(" [UNINSTALLER] NFC Game Launcher")
    print("=" * 70 + "\n")

    stop_running_script()
    remove_autostart_entry()
    remove_installation_dir()

    print("\n" + "=" * 70)
    print(" [SUCCESS] Desinstal·lació completada.")
    print("=" * 70 + "\n")
    
    input("Prem Enter per sortir...")