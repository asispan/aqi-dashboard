#!/usr/bin/env python3
"""AQI Dashboard server.

Reads a local air-quality monitor over HTTP, adds a one-hour weather forecast from
Open-Meteo, and serves an always-on, full-screen dashboard for a tablet.

Standard library only (Python 3.9+). Configure with config.json next to this file
(copy config.example.json). Run:  python3 server.py
"""
import datetime
import json
import math
import os
import re
import subprocess
import threading
import time
import urllib.request
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
CFG_PATH = os.environ.get("AQI_DASH_CONFIG", os.path.join(HERE, "config.json"))
DATA = os.path.expanduser(os.environ.get("AQI_DASH_DATA", "~/.local/share/aqi-dashboard"))


def load_config():
    with open(CFG_PATH) as f:
        cfg = json.load(f)
    cfg.setdefault("home_name", "Home")
    cfg.setdefault("listen", {"host": "0.0.0.0", "port": 8787})
    cfg.setdefault("monitor", {})
    cfg["monitor"].setdefault("type", "prana")
    cfg.setdefault("location", {})
    cfg.setdefault("forecast", True)
    cfg.setdefault("brightness", {"type": "none"})
    cfg.setdefault("power", {"type": "auto"})
    cfg.setdefault("kiosk", {"exit_command": ""})
    return cfg


CFG = load_config()
os.makedirs(DATA, exist_ok=True)
HIST_FILE = os.path.join(DATA, "history.jsonl")
PRESET_FILE = os.path.join(DATA, "preset.json")

state = {"aqi": None, "aqi_err": None, "wx": None, "wx_err": None}
hist = deque(maxlen=24 * 60)  # one reading a minute, 24 h
lock = threading.Lock()


def http_get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "aqi-dashboard"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode(errors="ignore")


# ---------------------------------------------------------------------------
# Monitor adapters. Each returns a dict with any of:
#   pm1, pm25, pm10 (ug/m3), temp (degC), hum (%RH), co2 (ppm)
# Add your own monitor type here and set monitor.type in config.json.
# ---------------------------------------------------------------------------
def read_prana(mon):
    """Prana Air / Bohu Monitor (ESP32). GET /data returns an HTML page of labels."""
    html = http_get(mon["url"], 6)
    labels = re.findall(r"<label[^>]*>([^<]*)</label>", html)
    d = {}
    if len(labels) > 1:
        d["pm25"] = float(labels[1])
    keys = {"PM1": "pm1", "PM10": "pm10", "Temp": "temp", "Humi": "hum"}
    for lab in labels:
        m = re.match(r"\s*(PM1|PM10|Temp|Humi)\s*:\s*([\d.]+)", lab)
        if m:
            d[keys[m[1]]] = float(m[2])
    co2 = re.search(r"CO2</label></div><div[^>]*><label >([\d.]+)", html)
    if co2:
        d["co2"] = float(co2[1])
    return d


def read_json(mon):
    """Any monitor with a JSON endpoint. monitor.fields maps our keys to dotted JSON paths."""
    doc = json.loads(http_get(mon["url"], 6))
    out = {}
    for key, path in mon.get("fields", {}).items():
        v = doc
        for part in path.split("."):
            v = v[int(part)] if isinstance(v, list) else v[part]
        out[key] = float(v)
    return out


ADAPTERS = {"prana": read_prana, "json": read_json}


def poll_monitor():
    mon = CFG["monitor"]
    reader = ADAPTERS[mon["type"]]
    while True:
        for _ in range(3):  # these little HTTP servers are single-connection and slow
            try:
                d = reader(mon)
                if "pm25" not in d:
                    raise ValueError("no PM2.5 in reading")
                d["ts"] = time.time()
                with lock:
                    state["aqi"], state["aqi_err"] = d, None
                    hist.append(d)
                with open(HIST_FILE, "a") as f:
                    f.write(json.dumps(d) + "\n")
                break
            except Exception as e:  # keep the last good reading on screen
                state["aqi_err"] = str(e)
                time.sleep(1)
        time.sleep(int(mon.get("interval_s", 60)))


def poll_forecast():
    loc = CFG["location"]
    if not CFG["forecast"] or "lat" not in loc:
        return
    url = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&current=is_day&hourly=weather_code,is_day,precipitation_probability"
           "&forecast_days=2&timezone=auto").format(**loc)
    while True:
        try:
            state["wx"], state["wx_err"] = json.loads(http_get(url, 15)), None
        except Exception as e:
            state["wx_err"] = str(e)
        time.sleep(600 if state["wx"] else 60)


def load_hist():
    try:
        cut = time.time() - 86400
        with open(HIST_FILE) as f:
            for line in f.readlines()[-3000:]:
                d = json.loads(line)
                if d.get("ts", 0) > cut:
                    hist.append(d)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Day / night: computed locally from the location (NOAA approximation), so the
# theme flips at local sunrise and sunset without any network call.
# ---------------------------------------------------------------------------
def sun_times(day, lat, lon, tz_hours):
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    x = math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(dec)) - math.tan(la) * math.tan(dec)
    ha = math.degrees(math.acos(max(-1.0, min(1.0, x))))
    noon = (720 - 4 * lon - eqt) / 60 + tz_hours
    return noon - ha / 15, noon + ha / 15


def theme():
    loc = CFG["location"]
    if "lat" not in loc:
        return None  # the page falls back to the forecast's is_day
    now = datetime.datetime.now()
    tz = time.localtime().tm_gmtoff / 3600
    rise, sset = sun_times(now.date(), loc["lat"], loc["lon"], tz)
    h = now.hour + now.minute / 60
    return "light" if rise <= h < sset else "dark"


# ---------------------------------------------------------------------------
# Optional device integrations (only when the server runs ON the tablet).
# ---------------------------------------------------------------------------
def power():
    if CFG["power"].get("type") == "none":
        return None
    base = "/sys/class/power_supply"
    try:
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            rd = lambda f: open(os.path.join(p, f)).read().strip()  # noqa: E731
            if os.path.exists(os.path.join(p, "online")) and os.path.exists(os.path.join(p, "status")):
                return {"status": rd("status"), "online": rd("online") == "1"}
    except Exception:
        pass
    return None


def bright():
    b = CFG["brightness"]
    if b.get("type") != "file":
        return None
    try:
        ov = open(b["override_file"]).read().strip()
        lvl = int(open(b["level_file"]).read().strip())
        return {"mode": "auto" if ov == "auto" else "manual", "level": lvl}
    except Exception:
        return None


def preset():
    try:
        with open(PRESET_FILE) as f:
            return json.load(f).get("id", "default")
    except Exception:
        return CFG.get("default_preset", "default")


def preset_mode():
    """'auto' follows sunrise/sunset; 'dark' locks the preset's night look."""
    try:
        with open(PRESET_FILE) as f:
            return json.load(f).get("mode", "auto")
    except Exception:
        return "auto"


def caps():
    return {"brightness": bright() is not None,
            "exit": bool(CFG["kiosk"].get("exit_command"))}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")  # kiosks must pick up new presets
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

    def _local(self):
        return self.client_address[0] in ("127.0.0.1", "::1")

    def do_GET(self):
        if self.path.startswith("/api/state"):
            with lock:
                out = {**state, "hist": list(hist), "now": time.time()}
            out.update(theme=theme(), power=power(), bright=bright(), preset=preset(), preset_mode=preset_mode(),
                       caps=caps(), home_name=CFG["home_name"],
                       temp_label=CFG.get("temp_label", "Outdoor temperature"),
                       sensor_name=CFG["monitor"].get("name", "Air quality monitor"))
            return self._json(out)
        super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/preset":
                body = self._body()
                pid = str(body["id"])
                with open(os.path.join(WEB, "presets", "index.json")) as f:
                    if pid not in {p["id"] for p in json.load(f)}:
                        raise ValueError("unknown preset")
                mode = body.get("mode", "auto")
                if mode not in ("auto", "dark"):
                    raise ValueError("mode must be auto or dark")
                with open(PRESET_FILE, "w") as f:
                    json.dump({"id": pid, "mode": mode}, f)
                return self._json({"ok": True})
            # Device controls are only accepted from the tablet itself.
            if not self._local():
                return self._json({"error": "device controls are local-only"}, 403)
            if self.path == "/api/brightness" and bright() is not None:
                d = self._body()
                val = "auto" if d.get("mode") == "auto" else str(max(8, min(255, int(d["level"]))))
                with open(CFG["brightness"]["override_file"], "w") as f:
                    f.write(val + "\n")
                return self._json({"ok": True})
            if self.path == "/api/exit" and caps()["exit"]:
                subprocess.Popen(CFG["kiosk"]["exit_command"], shell=True)
                return self._json({"ok": True})
            return self._json({"error": "not found"}, 404)
        except Exception as e:
            return self._json({"error": str(e)}, 400)


if __name__ == "__main__":
    load_hist()
    threading.Thread(target=poll_monitor, daemon=True).start()
    threading.Thread(target=poll_forecast, daemon=True).start()
    L = CFG["listen"]
    print(f"AQI dashboard on http://{L['host']}:{L['port']}/  (monitor: {CFG['monitor'].get('url')})")
    ThreadingHTTPServer((L["host"], int(L["port"])), Handler).serve_forever()
