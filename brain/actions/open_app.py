import time
import subprocess
import platform
import shutil
import os
import re
import shlex
import difflib
import json
import threading

from utils.logger import setup_logger
logger = setup_logger(__name__)

_SYSTEM = platform.system()
_APP_CACHE = None
_CACHE_LOCK = threading.Lock()

def _get_cache_path() -> str:
    if _SYSTEM == "Linux":
        cache_dir = os.path.expanduser("~/.cache/mia")
    elif _SYSTEM == "Windows":
        cache_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Mia")
    else:
        cache_dir = os.path.expanduser("~/Library/Caches/Mia")
        
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "app_cache.json")

def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    return name.replace(" ", "")

def _get_os_app_dirs() -> list[str]:
    if _SYSTEM == "Linux":
        return [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/flatpak/exports/share/applications",
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications")
        ]
    elif _SYSTEM == "Windows":
        return [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs")
        ]
    elif _SYSTEM == "Darwin":
        return ["/Applications", os.path.expanduser("~/Applications")]
    return []

def _get_max_mtime() -> float:
    max_mtime = 0.0
    for d in _get_os_app_dirs():
        if os.path.isdir(d):
            try:
                mtime = os.stat(d).st_mtime
                if mtime > max_mtime:
                    max_mtime = mtime
            except Exception:
                pass
    return max_mtime

def _add_to_cache(app_dict: dict, name: str, exec_basename: str, desktop_filename: str):
    global _APP_CACHE
    if not name:
        return
        
    keys = set()
    keys.add(normalize_name(name))
    if desktop_filename:
        clean_file = desktop_filename.rsplit('.', 1)[0]
        keys.add(normalize_name(clean_file))
    if exec_basename:
        keys.add(normalize_name(exec_basename))
        
    for k in keys:
        if k:
            _APP_CACHE[k] = app_dict

def discover_apps() -> dict:
    global _APP_CACHE
    if _APP_CACHE is not None:
        return _APP_CACHE
        
    with _CACHE_LOCK:
        if _APP_CACHE is not None:
            return _APP_CACHE

        cache_path = _get_cache_path()
        current_mtime = _get_max_mtime()
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("mtime", 0) >= current_mtime:
                        _APP_CACHE = data.get("cache", {})
                        logger.info("Loaded applications from persistent cache.")
                        return _APP_CACHE
            except Exception as e:
                logger.warning(f"Failed to load app cache: {e}")
        
        logger.info("Rebuilding application cache...")
        _APP_CACHE = {}
        if _SYSTEM == "Linux":
            discover_linux_apps()
        elif _SYSTEM == "Darwin":
            discover_macos_apps()
        elif _SYSTEM == "Windows":
            discover_windows_apps()
            
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({"mtime": current_mtime, "cache": _APP_CACHE}, f)
        except Exception as e:
            logger.warning(f"Failed to save app cache: {e}")

    return _APP_CACHE

def refresh_app_cache():
    global _APP_CACHE
    with _CACHE_LOCK:
        _APP_CACHE = None
    discover_apps()

def parse_desktop_file(path: str):
    name = None
    exec_cmd = None
    categories = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            in_desktop_entry = False
            for line in f:
                line = line.strip()
                if line == "[Desktop Entry]":
                    in_desktop_entry = True
                    continue
                elif line.startswith("[") and in_desktop_entry:
                    in_desktop_entry = False
                    continue
                
                if in_desktop_entry:
                    if line.startswith("Name="):
                        if not name:
                            name = line[5:]
                    elif line.startswith("Exec="):
                        if not exec_cmd:
                            exec_cmd = line[5:]
                    elif line.startswith("Categories="):
                        categories = line[11:].split(";")
                    elif line.startswith("NoDisplay=true") or line.startswith("Hidden=true"):
                        return
    except Exception:
        return
        
    if name and exec_cmd:
        clean_exec = re.sub(r'%[fFuUick]\b', '', exec_cmd).strip()
        
        try:
            parts = shlex.split(clean_exec)
            exec_basename = ""
            for p in parts:
                if "=" in p or p in ["env", "sh", "-c"]:
                    continue
                if p == "flatpak" and len(parts) > parts.index(p) + 2 and parts[parts.index(p)+1] == "run":
                    exec_basename = parts[parts.index(p)+2].split(".")[-1]
                    break
                exec_basename = os.path.basename(p)
                break
        except ValueError:
            exec_basename = ""
            
        app_dict = {
            "name": name,
            "exec": clean_exec,
            "path": path,
            "type": "desktop",
            "categories": categories,
            "desktop_file": os.path.basename(path)
        }
        _add_to_cache(app_dict, name, exec_basename, os.path.basename(path))

def discover_linux_apps():
    for d in _get_os_app_dirs():
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".desktop"):
                    path = os.path.join(root, file)
                    parse_desktop_file(path)

def discover_macos_apps():
    for d in _get_os_app_dirs():
        if not os.path.isdir(d):
            continue
        try:
            for folder in os.listdir(d):
                if folder.endswith(".app"):
                    path = os.path.join(d, folder)
                    name = folder[:-4]
                    app_dict = {
                        "name": name,
                        "path": path,
                        "type": "app"
                    }
                    _add_to_cache(app_dict, name, name, folder)
        except Exception:
            pass

def discover_windows_apps():
    for d in _get_os_app_dirs():
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".lnk"):
                    path = os.path.join(root, file)
                    name = file[:-4]
                    app_dict = {
                        "name": name,
                        "path": path,
                        "type": "shortcut"
                    }
                    _add_to_cache(app_dict, name, name, file)
                    
    try:
        import winreg
        for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            sub_key_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, sub_key_name) as sub_key:
                                try:
                                    display_name = winreg.QueryValueEx(sub_key, "DisplayName")[0]
                                except FileNotFoundError:
                                    continue
                                
                                app_dict = {
                                    "name": display_name,
                                    "type": "registry"
                                }
                                _add_to_cache(app_dict, display_name, "", "")
                        except OSError:
                            pass
            except FileNotFoundError:
                pass
    except Exception:
        pass

def _resolve_terminal() -> dict | None:
    if _SYSTEM == "Linux":
        if "TERMINAL" in os.environ and shutil.which(os.environ["TERMINAL"]):
            return {"exec": os.environ["TERMINAL"], "type": "executable", "name": "Terminal"}
        for t in ["xdg-terminal-exec", "x-terminal-emulator"]:
            if shutil.which(t):
                return {"exec": t, "type": "executable", "name": "Terminal"}
        for app in _APP_CACHE.values():
            if "TerminalEmulator" in app.get("categories", []):
                return app
        for t in ["ghostty", "kitty", "alacritty", "foot", "wezterm", "gnome-terminal", "konsole", "xfce4-terminal"]:
            if shutil.which(t):
                return {"exec": t, "type": "executable", "name": "Terminal"}
                
    elif _SYSTEM == "Darwin":
        if "TERMINAL" in os.environ and shutil.which(os.environ["TERMINAL"]):
            return {"exec": os.environ["TERMINAL"], "type": "executable", "name": "Terminal"}
        for t in ["Warp.app", "iTerm.app", "Terminal.app"]:
            path = os.path.join("/Applications", t)
            if os.path.exists(path):
                return {"path": path, "type": "app", "name": "Terminal"}
                
    elif _SYSTEM == "Windows":
        for t in ["wt.exe", "powershell.exe", "cmd.exe"]:
            if shutil.which(t):
                return {"exec": t, "type": "executable", "name": "Terminal"}
    return None

def _resolve_browser() -> dict | None:
    if _SYSTEM == "Linux":
        try:
            res = subprocess.check_output(["xdg-settings", "get", "default-web-browser"], text=True).strip()
            for app in _APP_CACHE.values():
                if app.get("desktop_file") == res:
                    return app
        except Exception:
            pass
        return {"exec": "xdg-open https://", "type": "shell", "name": "Browser"}
    elif _SYSTEM == "Darwin":
        return {"exec": "open https://", "type": "shell", "name": "Browser"}
    elif _SYSTEM == "Windows":
        return {"exec": "start https://", "type": "shell", "name": "Browser"}

def _resolve_files() -> dict | None:
    if _SYSTEM == "Linux":
        try:
            res = subprocess.check_output(["xdg-mime", "query", "default", "inode/directory"], text=True).strip()
            if "kitty" not in res.lower() and "terminal" not in res.lower():
                for app in _APP_CACHE.values():
                    if app.get("desktop_file") == res:
                        return app
        except Exception:
            pass
            
        for app in _APP_CACHE.values():
            if "FileManager" in app.get("categories", []):
                return app
        return {"exec": "xdg-open ~", "type": "shell", "name": "File Manager"}
    elif _SYSTEM == "Darwin":
        return {"exec": "open ~", "type": "shell", "name": "Finder"}
    elif _SYSTEM == "Windows":
        return {"exec": "explorer.exe", "type": "executable", "name": "Explorer"}

def _resolve_editor() -> dict | None:
    for env in ["VISUAL", "EDITOR"]:
        if env in os.environ and shutil.which(os.environ[env]):
            return {"exec": os.environ[env], "type": "executable", "name": "Editor"}
    if _SYSTEM == "Windows":
        return {"exec": "notepad.exe", "type": "executable", "name": "Editor"}
    return None

def _resolve_settings() -> dict | None:
    if _SYSTEM == "Windows":
        return {"exec": "ms-settings:", "type": "shell", "name": "Settings"}
    elif _SYSTEM == "Linux":
        for app in _APP_CACHE.values():
            if "Settings" in app.get("categories", []):
                return app
    return None

def resolve_system_role(name: str) -> dict | None:
    target = name.lower().strip()
    if target in ["terminal", "console", "shell"]:
        return _resolve_terminal()
    if target in ["browser", "web browser", "internet"]:
        return _resolve_browser()
    if target in ["files", "file manager", "folders", "explorer"]:
        return _resolve_files()
    if target in ["editor", "text editor"]:
        return _resolve_editor()
    if target == "settings":
        return _resolve_settings()
    return None

def find_application(name: str) -> dict | None:
    discover_apps()
    
    role_app = resolve_system_role(name)
    if role_app:
        return role_app
        
    norm_name = normalize_name(name)
    
    if norm_name in _APP_CACHE:
        return _APP_CACHE[norm_name]
        
    for k, v in _APP_CACHE.items():
        if k.startswith(norm_name):
            return v
            
    for k, v in _APP_CACHE.items():
        if norm_name in k:
            return v
            
    matches = difflib.get_close_matches(norm_name, _APP_CACHE.keys(), n=1, cutoff=0.75)
    if matches:
        return _APP_CACHE[matches[0]]
        
    return None

def launch_application(app: dict) -> bool:
    try:
        app_type = app.get("type")
        if app_type == "desktop" and "exec" in app:
            cmd = shlex.split(app["exec"])
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif app_type == "executable" and "exec" in app:
            subprocess.Popen([app["exec"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif app_type == "shell" and "exec" in app:
            subprocess.Popen(app["exec"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif app_type == "app" and "path" in app:
            subprocess.Popen(["open", app["path"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        elif app_type == "shortcut" and "path" in app:
            if hasattr(os, "startfile"):
                os.startfile(app["path"])
            else:
                subprocess.Popen(["start", app["path"]], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception as e:
        logger.exception("Launch failed")
    return False

def open_app(parameters=None, response=None, player=None, session_memory=None) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()
    if not app_name:
        return "No application name provided."
        
    if player:
        player.write_log(f"[open_app] {app_name}")
        
    app = find_application(app_name)
    
    if app:
        if launch_application(app):
            return f"Opened {app.get('name', app_name)}."
            
    if shutil.which(app_name):
        try:
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opened {app_name}."
        except Exception:
            pass
            
    if _SYSTEM == "Linux":
        try:
            result = subprocess.run(["gtk-launch", app_name], capture_output=True, timeout=5)
            if result.returncode == 0:
                return f"Opened {app_name}."
        except Exception:
            pass
            
    return f"Failed to open {app_name}: Could not find or launch application."