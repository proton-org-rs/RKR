"""Install both mode shortcuts for the current user, using this environment."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def desktop_quote(value):
    # freedesktop Exec quoting; percent is the field-code escape.
    result = str(value).replace("%", "%%")
    for character in ('\\', '"', '`', '$'):
        result = result.replace(character, '\\'+character)
    return '"'+result+'"'


def linux():
    desktop = Path.home()/"Desktop"
    xdg = shutil.which("xdg-user-dir")
    if xdg:
        result = subprocess.run([xdg, "DESKTOP"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            desktop = Path(result.stdout.strip())
    applications = Path(os.environ.get("XDG_DATA_HOME", str(Path.home()/".local/share")))/"applications"
    desktop.mkdir(parents=True, exist_ok=True)
    applications.mkdir(parents=True, exist_ok=True)
    for mode in ("operating", "testing"):
        content = (
            "[Desktop Entry]\nType=Application\nVersion=1.0\n"
            f"Name=SpiRob {mode.title()}\n"
            f"Comment=Three cable joystick · {mode}\n"
            f"Exec={desktop_quote(Path(sys.executable).absolute())} {desktop_quote(ROOT / ('run_'+mode+'.py'))}\n"
            f"Icon={ROOT / 'assets' / 'spirob.png'}\n"
            "Terminal=false\nCategories=Education;Science;Robotics;\n"
        )
        for destination in (desktop, applications):
            file = destination/f"spirob-{mode}.desktop"
            file.write_text(content, encoding="utf-8")
            file.chmod(0o755)
        print(f"Installed {desktop / ('spirob-'+mode+'.desktop')}")
        gio = shutil.which("gio")
        if gio:
            subprocess.run([gio, "set", str(desktop/f"spirob-{mode}.desktop"),
                            "metadata::trusted", "true"], capture_output=True, check=False)


def windows():
    python = Path(sys.executable).with_name("pythonw.exe")
    if not python.exists():
        python = Path(sys.executable)
    for mode in ("operating", "testing"):
        env = os.environ.copy()
        env.update(RKR_TARGET=str(python), RKR_ROOT=str(ROOT), RKR_ICON=str(ROOT/"assets/spirob.ico"),
                   RKR_ARGS=subprocess.list2cmdline([str(ROOT/f"run_{mode}.py")]),
                   RKR_NAME=f"SpiRob {mode.title()}.lnk")
        code = """
$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path $desktop $env:RKR_NAME))
$link.TargetPath = $env:RKR_TARGET
$link.Arguments = $env:RKR_ARGS
$link.WorkingDirectory = $env:RKR_ROOT
$link.IconLocation = $env:RKR_ICON
$link.Save()
"""
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", code],
                       env=env, check=True)
        print(f"Installed {env['RKR_NAME']}")


if __name__ == "__main__":
    if sys.platform == "win32":
        windows()
    elif sys.platform.startswith("linux"):
        linux()
    else:
        raise SystemExit("Shortcut installation supports Linux and Windows.")
