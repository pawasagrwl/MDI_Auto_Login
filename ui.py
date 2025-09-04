# ui.py
"""
MDI AutoLogin - UI / Tray module (Tk + pystray safe integration)

Usage: import ui and call ui.run_app() or run this file directly.
Requires: config.py, net.py (same API as earlier code).
"""

import sys, os, webbrowser, threading, random, time, ctypes
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw
import pystray
import logging

# Import helpers from your project
from config import (APP_NAME, DEFAULT_SSID, LOG_PATH,
                    load_config, save_config, get_password, set_password,
                    is_autostart_enabled, set_autostart)
from net import (connected_to_target, online_now, portal_intercept_present,
                 send_login, settle_until_online)

log = logging.getLogger("mdi.ui")

# native message boxes (thread-safe wins32)
MB_OK = 0
MB_ICONINFO = 0x40
MB_ICONERROR = 0x10
MB_YESNO = 0x04
IDYES = 6
def msg_info(title, text):
    ctypes.windll.user32.MessageBoxW(None, str(text), str(title), MB_OK | MB_ICONINFO)
def msg_error(title, text):
    ctypes.windll.user32.MessageBoxW(None, str(text), str(title), MB_OK | MB_ICONERROR)
def ask_yes_no(title, text) -> bool:
    return ctypes.windll.user32.MessageBoxW(None, str(text), str(title), MB_YESNO | MB_ICONINFO) == IDYES

# ---------- UI helpers ----------
def _sanitize_color(c: str) -> str:
    if not c or str(c).startswith("-"):
        return "SystemButtonFace"
    return str(c)

def ui_bg(root) -> str:
    st = ttk.Style(root)
    return _sanitize_color(st.lookup('TFrame', 'background') or root.cget('bg'))

def apply_theme(root, dark: bool):
    """Apply a simple, predictable light/dark theme for ttk + classic widgets."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    if dark:
        bg = "#121212"; fg = "#eaeaea"
        btn_bg = "#1e1e1e"; btn_active = "#2a2a2a"; btn_fg = fg
        entry_bg = "#1a1a1a"; entry_fg = fg
    else:
        bg = "#f6f6f6"; fg = "#111111"
        btn_bg = "#ffffff"; btn_active = "#e8e8e8"; btn_fg = "#111111"
        entry_bg = "#ffffff"; entry_fg = "#111111"

    style.configure(".", background=bg, foreground=fg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TButton", background=btn_bg, foreground=btn_fg, padding=(10,6))
    style.map("TButton",
              background=[("active", btn_active), ("pressed", btn_active)])
    # Ttk entry styling
    style.configure("TEntry", fieldbackground=entry_bg, foreground=entry_fg)
    style.configure("TCheckbutton", background=bg, foreground=fg)
    root.configure(bg=bg)

# ---------- Worker (unchanged) ----------
class AutoLoginWorker(threading.Thread):
    def __init__(self, tray_ref):
        super().__init__(daemon=True)
        self.tray_ref = tray_ref
        self.stop_event = threading.Event()
        self.running = False

    def run(self):
        cfg = load_config()
        username = cfg.get("username", "")
        password = get_password(username)
        self.tray_ref.update_tooltip(True)
        self.running = True
        while not self.stop_event.is_set():
            try:
                if connected_to_target(cfg):
                    if not online_now():
                        log.info("🔒 Logged out. Attempting login…")
                        ok = send_login(cfg, username, password)
                        if ok and settle_until_online(cfg["settle_max"], cfg["settle_step"]):
                            log.info("✅ Online confirmed.")
                        else:
                            log.info("⏳ Portal still intercepting; will retry.")
                            time.sleep(cfg["retry_wait"])
                    else:
                        log.info("✅ Already online.")
                else:
                    log.info("📶 Not on %s (or still acquiring).", cfg["ssid"])
            except Exception as e:
                log.info("⚠️ Worker loop error: %s", e)
            sleep_t = max(1.0, cfg["base_interval"] + random.uniform(-1, 1))
            # interruptible sleep
            end = time.time() + sleep_t
            while time.time() < end and not self.stop_event.is_set():
                time.sleep(0.2)
        self.running = False
        self.tray_ref.update_tooltip(False)

    def stop(self): self.stop_event.set()

# ---------- Settings Window ----------
class SettingsWindow:
    def __init__(self, parent_root, first_run=False):
        # parent_root is the hidden main Tk root so we always create Toplevel on GUI thread
        self.first_run = first_run
        self.root = tk.Toplevel(parent_root)
        self.root.title(f"{APP_NAME} — {'Welcome' if first_run else 'Settings'}")
        self.root.geometry("420x320")
        self.root.resizable(False, False)

        cfg = load_config()
        apply_theme(self.root, cfg.get("dark_mode", False))

        frm = ttk.Frame(self.root, padding=12); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Wi-Fi SSID:").grid(row=0, column=0, sticky="w")
        self.ent_ssid = ttk.Entry(frm, width=38); self.ent_ssid.insert(0, cfg.get("ssid", DEFAULT_SSID))
        self.ent_ssid.grid(row=0, column=1, sticky="we")

        ttk.Label(frm, text="Username:").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.ent_user = ttk.Entry(frm, width=38); self.ent_user.insert(0, cfg.get("username",""))
        self.ent_user.grid(row=1, column=1, sticky="we", pady=(8,0))

        ttk.Label(frm, text="Password:").grid(row=2, column=0, sticky="w", pady=(8,0))
        row = ttk.Frame(frm); row.grid(row=2, column=1, sticky="we", pady=(8,0))
        self.ent_pwd = ttk.Entry(row, width=30, show="•")
        self.ent_pwd.insert(0, get_password(cfg.get("username","")))
        self.ent_pwd.pack(side="left", fill="x", expand=True)
        self._pw_visible = False
        def toggle_pw():
            self._pw_visible = not self._pw_visible
            self.ent_pwd.configure(show="" if self._pw_visible else "•")
            btn_toggle.config(text="Hide" if self._pw_visible else "Show")
        btn_toggle = ttk.Button(row, text="Show", width=6, command=toggle_pw); btn_toggle.pack(side="left", padx=(6,0))

        ttk.Label(frm, text="Login URL:").grid(row=3, column=0, sticky="w", pady=(8,0))
        self.ent_url = ttk.Entry(frm, width=38)
        self.ent_url.insert(0, cfg.get("login_url", "https://172.16.16.16/24online/servlet/E24onlineHTTPClient"))
        self.ent_url.grid(row=3, column=1, sticky="we", pady=(8,0))

        self.btn_theme = ttk.Button(frm, text=("Light mode" if cfg.get("dark_mode", False) else "Dark mode"),
                                    command=self._toggle_theme)
        self.btn_theme.grid(row=4, column=0, columnspan=2, pady=(12,0))

        btns = ttk.Frame(frm); btns.grid(row=5, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="Save", command=self.on_save).pack(side="left", padx=(0,8))
        ttk.Button(btns, text="Cancel", command=self.on_cancel).pack(side="left")
        frm.columnconfigure(1, weight=1)

    def _toggle_theme(self):
        cfg = load_config()
        cfg["dark_mode"] = not cfg.get("dark_mode", False)
        save_config(cfg)
        apply_theme(self.root, cfg["dark_mode"])
        self.btn_theme.config(text=("Light mode" if cfg["dark_mode"] else "Dark mode"))

    def on_cancel(self):
        try: self.root.destroy()
        except Exception: pass

    def on_save(self):
        ssid = self.ent_ssid.get().strip() or DEFAULT_SSID
        user = self.ent_user.get().strip()
        pwd = self.ent_pwd.get()
        url = self.ent_url.get().strip() or "https://172.16.16.16/24online/servlet/E24onlineHTTPClient"
        if not user or not pwd:
            msg_error(APP_NAME, "Please enter username and password.")
            return
        cfg = load_config()
        cfg.update({"ssid": ssid, "username": user, "login_url": url, "first_run": False})
        save_config(cfg)
        set_password(user, pwd)
        log.info("💾 Settings saved.")
        try: self.root.destroy()
        except Exception: pass

        if self.first_run:
            if ask_yes_no(APP_NAME, "Start automatically when you sign in to Windows?"):
                exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])
                set_autostart(True, exe)
                msg_info(APP_NAME, "Enabled start with Windows.")
            else:
                set_autostart(False, "")

# ---------- Control Panel ----------
class ControlPanel:
    def __init__(self, parent_root, tray_app):
        # parent_root is the hidden main Tk root
        self.tray_app = tray_app
        self.root = tk.Toplevel(parent_root)
        self.root.title(f"{APP_NAME} — Control Panel")
        self.root.geometry("820x460")
        self.root.minsize(700, 380)

        self.cfg = load_config()
        apply_theme(self.root, self.cfg.get("dark_mode", False))

        top = ttk.Frame(self.root, padding=(12,10,12,6)); top.pack(fill="x")
        left = ttk.Frame(top); left.pack(side="left", fill="x", expand=True)

        self.status_canvas = tk.Canvas(left, width=16, height=16, highlightthickness=0, bd=0, bg=ui_bg(self.root))
        self.status_canvas.pack(side="left", padx=(0,8))
        self._status_dot = self.status_canvas.create_oval(2,2,14,14, fill="#999", outline="")

        self.lbl_status = ttk.Label(left, text=self._status_text(), anchor="w", justify="left")
        self.lbl_status.pack(side="left")

        # Quit in top-right
        ttk.Button(top, text="Quit", command=self._quit_app).pack(side="right")

        # Buttons row
        row = ttk.Frame(self.root, padding=(12,0,12,8)); row.pack(fill="x")
        self.btn_toggle = ttk.Button(row, text=self._toggle_text(), command=self._toggle_autologin)
        self.btn_toggle.pack(side="left", padx=(0,8))
        ttk.Button(row, text="Manual login now", command=self._manual_login).pack(side="left", padx=(0,8))
        ttk.Button(row, text="Settings…", command=self._open_settings).pack(side="left", padx=(0,8))

        util = ttk.Frame(row); util.pack(side="right")
        self.btn_startup = ttk.Button(util, text=self._startup_text(), command=self._toggle_startup)
        self.btn_startup.pack(side="left", padx=(0,8))
        ttk.Button(util, text="Open log", command=self._open_log).pack(side="left", padx=(0,8))
        self.btn_theme = ttk.Button(util, text=self._theme_text(), command=self._toggle_theme)
        self.btn_theme.pack(side="left")

        # Log viewer
        mid = ttk.Frame(self.root, padding=(12,4,12,12)); mid.pack(fill="both", expand=True)
        self.txt = tk.Text(mid, wrap="none", undo=False, font=("Consolas", 10), borderwidth=1, relief="solid")
        if self.cfg.get("dark_mode", False):
            self.txt.configure(bg="#0f0f0f", fg="#eaeaea", insertbackground="#eaeaea")
        else:
            self.txt.configure(bg="white", fg="#111111", insertbackground="black")
        self.scroll_y = ttk.Scrollbar(mid, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=self.scroll_y.set)
        self.txt.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")

        # schedule updates
        self._refresh_status()
        self._refresh_log()
        self._log_timer = None
        self._schedule_log_refresh()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # helper strings
    def _status_text(self):
        running = self.tray_app.worker is not None and self.tray_app.worker.running
        return f"SSID: {self.cfg.get('ssid', DEFAULT_SSID)}   |   Username: {self.cfg.get('username','') or '(not set)'}   |   Auto-login: {'Running' if running else 'Stopped'}"
    def _toggle_text(self):
        running = self.tray_app.worker is not None and self.tray_app.worker.running
        return "Stop auto-login" if running else "Start auto-login"
    def _startup_text(self):
        return "Disable start with Windows" if is_autostart_enabled() else "Enable start with Windows"
    def _theme_text(self):
        return "Light mode" if self.cfg.get("dark_mode", False) else "Dark mode"

    def _set_status_color(self, color: str):
        try:
            self.status_canvas.itemconfigure(self._status_dot, fill=color)
        except Exception:
            pass

    # actions
    def _toggle_autologin(self):
        if self.tray_app.worker and self.tray_app.worker.running:
            self.tray_app.stop_worker()
        else:
            self.tray_app.start_worker()
        self._refresh_status()

    def _manual_login(self):
        cfg = load_config()
        user = cfg.get("username", ""); pwd = get_password(user)
        if not user or not pwd:
            msg_info(APP_NAME, "Set username/password in Settings first.")
            return
        if not connected_to_target(cfg):
            self._set_status_color("#FFA000")
            msg_info(APP_NAME, f"Not on {cfg['ssid']} yet.")
            return
        ok = send_login(cfg, user, pwd)
        if ok:
            settled = settle_until_online(cfg["settle_max"], cfg["settle_step"])
            self._set_status_color("#28a745" if settled else "#FFA000")
            msg_info(APP_NAME, "Login sent." + (" Online." if settled else " Waiting for portal…"))
        else:
            self._set_status_color("#E53935")
            msg_error(APP_NAME, "Could not send login request.")
        self._refresh_log()

    def _open_settings(self):
        SettingsWindow(self.root, first_run=False)
        # settings window is a Toplevel; after it closes, reload config
        self.cfg = load_config()
        self._refresh_status()
        # update text widget colors to match theme
        if self.cfg.get("dark_mode", False):
            self.txt.configure(bg="#0f0f0f", fg="#eaeaea", insertbackground="#eaeaea")
            self.status_canvas.configure(bg="#121212")
        else:
            self.txt.configure(bg="white", fg="#111111", insertbackground="black")
            self.status_canvas.configure(bg=ui_bg(self.root))

    def _toggle_startup(self):
        exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])
        set_autostart(not is_autostart_enabled(), exe)
        self._refresh_status()

    def _open_log(self):
        try:
            webbrowser.open(LOG_PATH.as_uri())
        except Exception:
            os.startfile(str(LOG_PATH))

    def _toggle_theme(self):
        self.cfg["dark_mode"] = not self.cfg.get("dark_mode", False)
        save_config(self.cfg)
        apply_theme(self.root, self.cfg["dark_mode"])
        # update text widget & canvas colors
        if self.cfg["dark_mode"]:
            self.txt.configure(bg="#0f0f0f", fg="#eaeaea", insertbackground="#eaeaea")
            self.status_canvas.configure(bg="#121212")
        else:
            self.txt.configure(bg="white", fg="#111111", insertbackground="black")
            self.status_canvas.configure(bg=ui_bg(self.root))
        self.btn_theme.config(text=self._theme_text())

    def _quit_app(self):
        self.tray_app.stop_worker()
        self._cancel_log_refresh()
        try: self.root.destroy()
        except Exception: pass
        try: self.tray_app.icon.stop()
        except Exception: pass

    def _refresh_status(self):
        color = "#28a745" if online_now() else ("#FFA000" if portal_intercept_present() or connected_to_target(self.cfg) else "#999999")
        self._set_status_color(color)
        try:
            self.lbl_status.config(text=self._status_text())
            self.btn_toggle.config(text=self._toggle_text())
            self.btn_startup.config(text=self._startup_text())
        except Exception:
            pass

    def _refresh_log(self):
        try:
            txt = LOG_PATH.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            txt = "(log not available yet)"
        lines = txt.splitlines()
        txt = "\n".join(lines[-400:])
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", txt)
        self.txt.see("end")

    def _schedule_log_refresh(self):
        self._log_timer = self.root.after(2000, self._on_log_tick)

    def _on_log_tick(self):
        try:
            self._refresh_log()
            self._refresh_status()
        finally:
            if self.root.winfo_exists():
                self._schedule_log_refresh()

    def _cancel_log_refresh(self):
        try:
            if self._log_timer:
                self.root.after_cancel(self._log_timer)
        except Exception:
            pass

    def _on_close(self):
        self._cancel_log_refresh()
        try: self.root.destroy()
        except Exception: pass

# ---------- Tray App ----------
class TrayApp:
    def __init__(self, tk_root):
        # tk_root is the hidden main Tk instance (must run in main thread)
        self.tk_root = tk_root
        self.panel = None
        self.icon = pystray.Icon("mdi_tray")
        self.worker = None
        self.icon.icon = self._build_icon()
        self.icon.title = APP_NAME
        self.update_tooltip(False)

        # menu
        self.icon.menu = pystray.Menu(
            pystray.MenuItem("Open Control Panel", self.open_control_panel, default=True),
            pystray.MenuItem("Start auto-login", self.start_worker),
            pystray.MenuItem("Stop auto-login", self.stop_worker),
            pystray.MenuItem("Manual login now", self.manual_login),
            pystray.MenuItem("Settings…", self.open_settings),
            pystray.MenuItem("Open log", self.open_log),
            pystray.MenuItem("Quit", self.quit)
        )

    def _build_icon(self):
        img = Image.new("RGBA", (24, 24), (0,0,0,0))
        d = ImageDraw.Draw(img)
        d.arc([2,10,22,22], 200, 340, fill=(255,255,255,255), width=2)
        d.arc([5,12,19,22], 200, 340, fill=(255,255,255,255), width=2)
        d.arc([8,14,16,22], 200, 340, fill=(0,180,255,255), width=2)
        d.ellipse([10,18,14,22], fill=(0,180,255,255))
        return img

    def update_tooltip(self, running: bool):
        self.icon.title = f"{APP_NAME} — {'Running' if running else 'Idle'}"

    # All UI actions scheduled on tk_root to run in GUI thread
    def open_control_panel(self, _=None):
        def _show_panel():
            # if open, bring to front
            if getattr(self, "panel", None) and self.panel.root.winfo_exists():
                try:
                    self.panel.root.deiconify()
                    self.panel.root.lift()
                    self.panel.root.focus_force()
                except Exception:
                    pass
                return
            # create panel Toplevel
            self.panel = ControlPanel(self.tk_root, self)
        self.tk_root.after(0, _show_panel)

    def start_worker(self, _=None):
        if self.worker and self.worker.running:
            return
        self.worker = AutoLoginWorker(self)
        self.worker.start()
        log.info("▶️ Auto-login started.")
        self.update_tooltip(True)

    def stop_worker(self, _=None):
        if self.worker:
            self.worker.stop()
            self.worker = None
        log.info("⏹️ Auto-login stopped.")
        self.update_tooltip(False)

    def manual_login(self, _=None):
        cfg = load_config()
        user = cfg.get("username",""); pwd = get_password(user)
        if not user or not pwd:
            msg_info(APP_NAME, "Please set username/password in Settings first.")
            return
        if not connected_to_target(cfg):
            msg_info(APP_NAME, f"Not on {cfg['ssid']} yet.")
            return
        ok = send_login(cfg, user, pwd)
        if ok:
            settled = settle_until_online(cfg["settle_max"], cfg["settle_step"])
            msg_info(APP_NAME, "Login sent." + (" Online." if settled else " Waiting for portal…"))
        else:
            msg_error(APP_NAME, "Could not send login request.")

    def open_settings(self, _=None):
        # open settings as Toplevel on GUI thread
        def _open():
            SettingsWindow(self.tk_root, first_run=False)
        self.tk_root.after(0, _open)

    def open_log(self, _=None):
        try:
            webbrowser.open(LOG_PATH.as_uri())
        except Exception:
            os.startfile(str(LOG_PATH))

    def quit(self, _=None):
        # stop worker and icon
        self.stop_worker()
        try:
            self.icon.stop()
        except Exception:
            pass
        # schedule Tk root shutdown
        def _stop_tk():
            try: self.tk_root.quit()
            except Exception: pass
        self.tk_root.after(0, _stop_tk)

    def run(self):
        """Start the tray icon in a background thread, keep the Tk root mainloop running."""
        # If first-run or no username, show settings first
        cfg = load_config()
        if cfg.get("first_run", True) or not cfg.get("username"):
            # show settings on GUI thread and wait for it to be closed before continuing
            done = threading.Event()
            def _show_first_run():
                SettingsWindow(self.tk_root, first_run=True)
                done.set()
            self.tk_root.after(0, _show_first_run)
            # run a short loop until done (tk mainloop will be started by caller)
            while not done.is_set():
                time.sleep(0.1)

        # run the tray icon in a separate thread (pystray will create its own message loop)
        t = threading.Thread(target=self.icon.run, daemon=True)
        t.start()

# ---------- Entrypoint helper ----------
def run_app():
    # must create Tk root in main thread
    root = tk.Tk()
    root.withdraw()  # hidden root used for creating Toplevels
    app = TrayApp(root)
    # start tkinter mainloop on main thread and run app
    try:
        app.run()
        root.mainloop()
    finally:
        # ensure icon stopped on exit
        try: app.icon.stop()
        except Exception: pass

if __name__ == "__main__":
    # run it directly for quick testing: python ui.py
    logging.basicConfig(level=logging.INFO)
    run_app()
