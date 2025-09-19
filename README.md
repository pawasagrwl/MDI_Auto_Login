# MDI AutoLogin App

This is a lightweight Windows tray application that automatically logs you into the **MDI Wi-Fi captive portal**.
It runs silently in the background with a tray icon, auto-logins when required, and gives you a control panel for monitoring and managing.

---

## ✨ Features

* 🔑 **Automatic Wi-Fi login** when connected to the MDI network.
* 🔒 **Secure credential storage** via Windows Credential Manager.
* 🖥 **System tray integration** with:

  * Start/stop auto-login.
  * Manual login trigger.
  * Settings (SSID, username, password, login URL).
  * Log viewer (with live updates).
  * Reset options: **reset log**, **reset settings**, or **reset entire app**.
* 🎨 **Light/dark theme toggle** with themed control panel and log viewer.
* 🚀 **Auto-start with Windows** option.
* 📡 **Live status indicator**: connection state shown with both text and background color (Online / Waiting / Offline).

---

## 📦 Installation (for users)

1. Go to the [Releases](../../releases) page.
2. Download the latest installer/exe (`mdi_autologin.exe`).
3. Run the app. On first run, you’ll see the **Settings** window to configure SSID, username, and password.
4. The tray icon will appear in the Windows system tray (bottom-right).

From now on, login will happen automatically whenever you connect to MDI Wi-Fi.

---

## 🛠 Development / Testing

Requirements:

* **Python 3.10+**
* Dependencies:

  ```bash
  pip install pyinstaller pystray pillow keyring requests
  ```

Run for development:

```bash
cd app
python app.py
```

* On first run, the **Settings** window appears.
* The tray icon will then appear in the Windows system tray.
* Right-click for menu options, or left-click → **Open Control Panel**.

Logs are saved at:

```
C:\Users\<YourName>\AppData\Local\MDI_AutoLogin\mdi_autologin.log
```

---

## 🏗 Building Manually (for contributors)

If you want to package the app yourself (instead of using the release binaries):

```bash
cd app
pyinstaller --noconsole --onefile --icon=mdi.ico app.py
```

Options:

* `--noconsole` → no black console window.
* `--onefile` → bundle into single .exe.
* `--icon=mdi.ico` → custom tray icon (optional).

The built executable will appear in:

```
dist/app.exe
```

---

## ⚙️ CI/CD (GitHub Actions)

* This project is configured with **GitHub Actions**.
* Every new **tag push** (`vX.Y.Z`) automatically:

  * Builds the Windows executable.
  * Uploads it as a Release on GitHub.

So end users don’t need to build manually — just grab the latest release binary.

---

## 📝 Notes

* Credentials are stored securely in Windows Credential Manager.
* If you move between routers on campus, the app re-detects the MDI SSID and re-logins automatically.
* If auto-login is paused, you can use **Manual login now**.
* Use **Reset options** in the control panel if you want to clear log, reset credentials, or reset the app completely.
