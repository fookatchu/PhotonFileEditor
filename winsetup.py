# This script is working but needs a major overhaulling
# Check https://github.com/makewitharduino/Scratio/blob/master/setup.py for inspiration
# X3msnake 180726
#
################################
#
#just build	 			python winsetup.py build -b ..\							#Builds on the folder above
#build installer		python winsetup.py build -b ..\  bdist_msi -d ..\		#Builds on the folder above
#
################################

import os
import sys
from cx_Freeze import setup, Executable

# https://stackoverflow.com/questions/15734703/use-cx-freeze-to-create-an-msi-that-adds-a-shortcut-to-the-desktop
# http://msdn.microsoft.com/en-us/library/windows/desktop/aa371847(v=vs.85).aspx
shortcut_table = [
    ("DesktopShortcut",												# Shortcut
     "DesktopFolder",												# Directory_
     "PhotonFileEditor",											# Name
     "TARGETDIR",													# Component_
     "[TARGETDIR]PhotonEditor.exe",									# Target
     None,															# Arguments
     None,															# Description
     None,															# Hotkey
     "C:\Program Files (x86)\PhotonFileEditor\photonsters.ico",		# Icon
     None,															# IconIndex
     None,															# ShowCmd
     'TARGETDIR'               										# WkDir
     )
    ]

# Now create the table dictionary
msi_data = {"Shortcut": shortcut_table}

# Change some default MSI options and specify the use of the above defined tables
bdist_msi_options = {'data': msi_data}

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os", "OpenGL"],"include_files": [""], "include_msvcr" : True}

PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(  name = "PhotonFileEditor",
        version = "0.1",
		author= "Photonsters",
		url="https://github.com/Photonsters",
        description = "Photon File Editor",
        options = {"build_exe": build_exe_options,"bdist_msi": bdist_msi_options},
        executables = [Executable("PhotonEditor.py", base=base,)])