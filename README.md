# MDI AutoLogin App

This is a Windows tray application that automatically logs you into the MDI Wi-Fi captive portal.  
It provides a tray icon with a control panel for settings, manual login, and viewing logs.

---

## Features
- Automatic Wi-Fi login when connected to MDI.
- Secure credential storage (Windows Credential Manager via `keyring`).
- System tray icon with:
  - Start/stop auto-login.
  - Manual login button.
  - Settings (SSID, username, password, login URL).
  - Open log viewer.
- Dark/light theme toggle.
- Option to start with Windows.

---

## Requirements (for development/testing)
- Python 3.10+ installed
- The following Python packages:
  ```bash
  pip install pyinstaller pystray pillow keyring requests

---

## Running for Development

From the project root:

```bash
cd app
python app.py
```

* On first run, a **Settings window** will appear to configure username, password, and SSID.
* The tray icon will then appear in the Windows system tray (bottom-right).
* Right-click the tray icon for options, or left-click **Open Control Panel**.

Logs are saved at:

```
C:\Users\<YourName>\AppData\Local\MDI_AutoLogin\mdi_autologin.log
```

---

## Building a Standalone EXE

To package the app into a single `.exe` that works on any Windows PC (no Python required):

1. Install PyInstaller (if not already done):

   ```bash
   pip install pyinstaller
   ```

2. (Optional) Prepare an icon (`mdi.ico`) in the project folder.

3. Run PyInstaller:

   ```bash
   cd app
   pyinstaller --noconsole --onefile --icon=mdi.ico app.py
   ```

   * `--noconsole` → no black console window.
   * `--onefile` → single `.exe` file.
   * `--icon=mdi.ico` → sets a custom tray icon (optional).

4. The built executable will be in:

   ```
   dist/app.exe
   ```

---

## First Run

* Double-click `app.exe`.
* The **Settings window** will appear.
* Enter your **SSID**, **username**, and **password**.
* Save settings.
* The tray icon will appear and auto-login will start.

On first run, the app will also ask if you want it to start automatically with Windows.

---

## Notes

* Credentials are stored securely using the Windows Credential Manager.
* If you move between routers on campus, the app still detects the MDI network and re-logins.
* Use the "Manual login now" option if auto-login is stopped.

---
