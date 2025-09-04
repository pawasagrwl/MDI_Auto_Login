# net.py
import re, subprocess, time, requests, urllib3, logging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
log = logging.getLogger("mdi")

def any_connected_ssid(ssid: str) -> bool:
    try:
        out = subprocess.check_output("netsh wlan show interfaces", shell=True).decode(errors="ignore")
        blocks = re.split(r"\r?\n\s*Name\s*:", out)
        for b in blocks:
            if not b.strip(): continue
            if re.search(r"State\s*:\s*connected", b, re.I):
                m = re.search(r"SSID\s*:\s*(.+)", b, re.I)
                if m and ssid.lower() in m.group(1).strip().lower():
                    return True
    except Exception:
        pass
    return False

def gateway_is_campus() -> bool:
    try:
        out = subprocess.check_output("ipconfig", shell=True).decode(errors="ignore")
        for gw in re.findall(r"Default Gateway[^\r\n]*:\s*([\d\.]+)", out, re.I):
            if gw.startswith("172.16."): return True
    except Exception:
        pass
    return False

def portal_intercept_present() -> bool:
    try:
        r = requests.get("http://clients3.google.com/generate_204",
                         timeout=3, verify=False, allow_redirects=True)
        return ("172.16." in r.url) or ("24online" in r.text.lower())
    except Exception:
        return False

def connected_to_target(cfg) -> bool:
    return any_connected_ssid(cfg["ssid"]) or gateway_is_campus() or portal_intercept_present()

def online_now() -> bool:
    try:
        r = requests.get("http://clients3.google.com/generate_204",
                         timeout=3, verify=False, allow_redirects=True)
        return not(("172.16." in r.url) or ("24online" in r.text.lower()))
    except Exception:
        return False

def send_login(cfg, username: str, password: str) -> bool:
    payload = {"mode":"191","username":username,"password":password}
    try:
        r = requests.post(cfg["login_url"], data=payload,
                          timeout=cfg["post_timeout"], verify=False, allow_redirects=True)
        log.info("📨 Login POST sent (status %s).", r.status_code)
        return True
    except Exception as e:
        log.info("❌ Error sending login POST: %s", e)
        return False

def settle_until_online(max_s: float, step: float) -> bool:
    waited = 0.0
    while waited < max_s:
        if online_now(): return True
        time.sleep(step); waited += step
    return False
