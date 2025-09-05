# config.py
import os, json, sys, logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import winreg
import keyring

APP_NAME = "MDI AutoLogin"
SERVICE_NAME = "MDI_AutoLogin"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
DEFAULT_SSID = "MDI"

def app_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    p = Path(base) / SERVICE_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

CONFIG_PATH = app_dir() / "config.json"
LOG_PATH    = app_dir() / "mdi_autologin.log"

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "ssid": DEFAULT_SSID,
        "username": "",
        "login_url": "https://172.16.16.16/24online/servlet/E24onlineHTTPClient",
        "base_interval": 5,
        "retry_wait": 3,
        "post_timeout": 8,
        "settle_max": 8,
        "settle_step": 0.5,
        "first_run": True,
        "auto_start_on_launch": True, 
        "dark_mode": False,
    }

def save_config(cfg): CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def get_password(username: str) -> str:
    return keyring.get_password(SERVICE_NAME, username) or "" if username else ""

def set_password(username: str, password: str):
    if username:
        keyring.set_password(SERVICE_NAME, username, password)

def _run_value_name() -> str: return SERVICE_NAME

def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, _run_value_name())
            return True
    except OSError:
        return False

def set_autostart(enable: bool, exe_path: str):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, _run_value_name(), 0, winreg.REG_SZ, f"\"{exe_path}\"")
            else:
                try: winreg.DeleteValue(k, _run_value_name())
                except OSError: pass
    except OSError as e:
        logging.getLogger("mdi").info("Autostart change failed: %s", e)

def setup_logger():
    lg = logging.getLogger("mdi")
    lg.setLevel(logging.INFO)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=512*1024, backupCount=3, encoding="utf-8", delay=True)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    lg.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    lg.addHandler(sh)
    lg.info("Log file: %s", LOG_PATH)
    return lg
