# NFC_FLOPPY_INSTALLER
An open-source DIY project that bridges physical retro media with modern digital storefronts. Insert a physical (or 3D-printed) floppy disk into a custom 3D-printed drive, and it will automatically check your library, install, or launch your games on **Steam**, **GOG**, or **ScummVM**.

---

##  How It Works

1. **The Hardware:** A hidden **NFC reader** is housed inside a custom 3D-printed floppy disk drive.
2. **The Media:** You use real floppy disks or 3D-printed ones with an NFC sticker hidden discreetly underneath the game's custom label.
3. **The Software:** When a disk is inserted, the background script reads the NFC tag, identifies the game, and queries your accounts:
   * **If owned but not installed:** It triggers the installation.
   * **If already installed:** It launches the game directly.

---

## ️ Project Structure

```text
├── software/           # Python source code and execution scripts
├── hardware/           
│   ├── source/         # Blender source files (.blend)
│   ├── generator/      # Python scripts for generating custom 3D parts
│   └── stl/            # Ready-to-print STL files
├── .gitignore          # Git exclusion rules
└── LICENSE             # Licensing details (Dual-licensed)
```

## Hardware & 3D Printing

To build the enclosure and disks, check the hardware/ directory for the custom internal mount for the NFC reader.

    Floppy Disks: For the physical disks, this project is designed to use or adapt the models found here: Thingiverse - 3D Printed Floppy Disk.

    Assembly Tip: Place a standard NFC sticker (like NTAG213) flat against the disk surface before applying your custom game label over it to keep it completely hidden.
	
## Software Setup
Prerequisites

    Python 3.x installed on your system.

    A compatible NFC reader connected via USB (e.g., RC522 or PN532-based setups, depending on your configuration).
	
## 

 Licensing

This project is dual-licensed to appropriately cover both physical design and software components:

    Hardware & 3D Models: Licensed under the Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).

    Software : Licensed under the GNU General Public License v3.0 (GPLv3).
