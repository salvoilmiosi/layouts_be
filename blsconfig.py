from pathlib import Path
import os
import sys

if sys.platform == 'win32':
    import winreg

    def getconfig(name):
        try:
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\BillLayoutScript", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(reg_key, name)
            winreg.CloseKey(reg_key)
            return value
        except WindowsError:
            return None
else:
    with open(os.getenv('HOME')+'/.BillLayoutScript', 'r') as file:
        input_config = file.read()
    
    def getconfig(name):
        for line in input_config.splitlines():
            if line.startswith('['):
                return None
            else:
                equals=line.index('=')
                if line[:equals] == name: return line[equals+1:]
        return None

pybls_path = str(Path(getconfig('PyBlsPath')).resolve())
os.environ['PATH'] = pybls_path + os.pathsep + os.environ['PATH']
sys.path.insert(0, pybls_path)
execbls = __import__("pybls").execbls

control_script_path = Path(getconfig('ControlScriptFilename'))
pdfs_path = Path(getconfig('PdfsPath'))
read_output_path = Path(getconfig('ReadOutputPath'))
google_drive_dir = Path(getconfig('GoogleDriveDir'))