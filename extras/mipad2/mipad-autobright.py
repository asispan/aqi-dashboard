#!/usr/bin/env python3
"""Mi Pad 2 auto-brightness: drives the TI LP8556 backlight (i2c-1 @0x2c, reg 0x00) directly.

Day (sunrise..sunset at AB_LAT/AB_LON, computed locally): full brightness.
Night: follows the ambient light sensor (HID ALS) on a log curve, smoothed, with a floor.
Overrides: /run/mipad-autobright/override  -> "auto" | "<0-255>"  (manual hold until set back to auto)
"""
import fcntl, math, os, subprocess, time, datetime

BUS, ADDR, REG = "/dev/i2c-1", 0x2C, 0x00
I2C_SLAVE_FORCE = 0x0706
ALS = "/sys/bus/iio/devices/iio:device1"
import os as _os, time as _time
# Set your location (city-level is enough) in /etc/default/mipad-autobright or the environment.
LAT = float(_os.environ.get("AB_LAT", "0"))
LON = float(_os.environ.get("AB_LON", "0"))
TZ = _time.localtime().tm_gmtoff / 3600
DAY_LEVEL, MIN_LEVEL, MAX_LEVEL = 255, 14, 255
TWILIGHT_MIN = 30          # ramp minutes around sunrise/sunset
POLL = 2.0
STATE = "/run/mipad-autobright"

def sun_times(d):
    """NOAA approximation -> (sunrise, sunset) as local-hour floats."""
    n = d.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lat = math.radians(LAT)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(lat) * math.cos(dec))
                                - math.tan(lat) * math.tan(dec)))
    noon = (720 - 4 * LON - eqt) / 60 + TZ
    return noon - ha / 15, noon + ha / 15

def day_weight(now):
    """1.0 in full day, 0.0 at night, linear ramp over TWILIGHT_MIN around sunrise/sunset."""
    rise, sset = sun_times(now.date())
    h = now.hour + now.minute / 60 + now.second / 3600
    r = TWILIGHT_MIN / 60
    if rise + r <= h <= sset - r: return 1.0
    if h <= rise - r or h >= sset + r: return 0.0
    if h < 12: return (h - (rise - r)) / (2 * r)
    return ((sset + r) - h) / (2 * r)

def read_lux():
    try:
        raw = subprocess.run(["cat", f"{ALS}/in_illuminance_raw"], capture_output=True, text=True, timeout=2).stdout
        scale = float(open(f"{ALS}/in_illuminance_scale").read()) if os.path.exists(f"{ALS}/in_illuminance_scale") else 1.0
        return float(raw) * scale
    except Exception:
        return None

def lux_to_level(lux):
    # 0 lux -> MIN, ~10 lux (dim room) -> ~60, ~100 lux (lit room) -> ~150, >=1000 lux -> MAX
    if lux is None: return None
    f = min(1.0, max(0.0, math.log10(lux + 1) / 3.0))
    return MIN_LEVEL + (MAX_LEVEL - MIN_LEVEL) * f

class Backlight:
    def __init__(s):
        s.fd = os.open(BUS, os.O_RDWR); fcntl.ioctl(s.fd, I2C_SLAVE_FORCE, ADDR); s.cur = None
    def set(s, v):
        v = int(max(0, min(255, round(v))))
        if v != s.cur:
            os.write(s.fd, bytes([REG, v])); s.cur = v
            with open(f"{STATE}/level", "w") as f: f.write(str(v))

def override():
    try: return open(f"{STATE}/override").read().strip()
    except FileNotFoundError: return "auto"

def main():
    os.makedirs(STATE, exist_ok=True)
    if not os.path.exists(f"{STATE}/override"):
        open(f"{STATE}/override", "w").write("auto\n")
    os.chmod(f"{STATE}/override", 0o666)
    bl, smooth, last_auto, was_manual = Backlight(), None, 0.0, False
    while True:
        ov = override()
        if ov.isdigit():                      # manual hold from the dashboard slider
            bl.set(max(8, min(255, int(ov))))  # floor 8: never fully black
            was_manual = True
            if time.time() - last_auto >= POLL:  # keep the sun signal fresh: the theme follows it
                last_auto = time.time()
                w = day_weight(datetime.datetime.now())
                with open(f"{STATE}/status", "w") as f:
                    f.write(f"lux=manual day_weight={w:.2f} target={bl.cur} level={bl.cur}\n")
            time.sleep(0.15); continue
        if was_manual:                        # back to auto: fade from the manual level
            smooth, was_manual, last_auto = bl.cur, False, 0.0
        if time.time() - last_auto < POLL:
            time.sleep(0.15); continue
        last_auto = time.time()
        lux = read_lux()
        night = lux_to_level(lux)
        if night is None: night = 90  # sensor glitch at night: safe middle
        w = day_weight(datetime.datetime.now())
        target = w * DAY_LEVEL + (1 - w) * night
        smooth = target if smooth is None else smooth + (target - smooth) * 0.25
        if bl.cur is None or abs(smooth - bl.cur) >= 3 or (w == 1.0 and bl.cur != DAY_LEVEL):
            bl.set(DAY_LEVEL if w == 1.0 else smooth)
        with open(f"{STATE}/status", "w") as f:
            f.write(f"lux={lux} day_weight={w:.2f} target={target:.0f} level={bl.cur}\n")

if __name__ == "__main__":
    main()
