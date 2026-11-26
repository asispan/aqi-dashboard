# Android tablet (no root needed)

There are two ways to run it. With option B, the tablet only shows the dashboard and the server runs elsewhere.

## A. Everything on the tablet

1. Install [Termux](https://f-droid.org/packages/com.termux/) from F-Droid, then:
   ```bash
   pkg install python git
   git clone https://github.com/asispan/aqi-dashboard && cd aqi-dashboard/app
   cp config.example.json config.json && nano config.json
   python server.py
   ```
2. Keep it alive: in Termux, pull down the notification and choose **Acquire wakelock**. Exclude Termux from battery optimisation.
3. **To start at boot:** install the Termux:Boot add-on, then put `cd ~/aqi-dashboard/app && python server.py` in `~/.termux/boot/start.sh`.

## B. Server on another machine

Follow [`deploy/host`](../host) and use `http://<host-ip>:8787/` as the URL below.

## Kiosk: Fully Kiosk Browser

[Fully Kiosk Browser](https://www.fully-kiosk.com/) turns any Android tablet into a locked, always-on display. Set these options:

| Setting | Value |
|---|---|
| Start URL | `http://127.0.0.1:8787/` (A) or `http://<host-ip>:8787/` (B) |
| Kiosk mode | On, with a kiosk PIN |
| Keep screen on | On |
| Launch on boot | On |
| Advanced Web Settings → Enable JavaScript Interface | On *(PLUS licence)* |

With the JavaScript Interface enabled, the dashboard detects Fully automatically:

- The **brightness card** controls the real screen brightness (`fully.setScreenBrightness`).
- The **charging icon** shows the real state (`fully.isPlugged`).
- **Exit app** closes the kiosk (`fully.exit`).

Because the JavaScript Interface lets pages control the device, also set **Web Content Filtering → URL Whitelist** to your dashboard URL only.

Without the PLUS licence the dashboard still works full screen. The brightness card then shows sensor status, and you leave the kiosk using Fully's own PIN gesture.

**Free alternative:** use Chrome, **Add to Home screen**, plus Android's **Screen pinning** (Settings → Security). Turn on **Stay awake while charging** in Developer options.
