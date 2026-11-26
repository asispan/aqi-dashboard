# iPad (no jailbreak needed)

The iPad is the display. The server runs on another always-on machine ([`deploy/host`](../host)).

1. **Install as an app.** In Safari, open `http://<host-ip>:8787/`, tap **Share → Add to Home Screen**, then open it from the Home Screen. It runs full screen, with no Safari bars.
2. **Never sleep.** **Settings → Display & Brightness → Auto-Lock → Never.**
3. **Lock it in (kiosk).**
   1. Turn on **Settings → Accessibility → Guided Access**, then set a passcode.
   2. In **Display Auto-Lock**, choose **Never**.
   3. Open the dashboard and triple-click the top (or side) button.
   4. Tap **Start**.
4. **Brightness.** iPadOS manages it: turn on **Auto-Brightness** (Settings → Accessibility → Display & Text Size). A web page can't set the iPad's brightness, so the brightness card turns into a sensor-status card.
5. **Power.** Keep it plugged in.

## Presets and Exit app

- **Open the preset picker:** press and hold the home name (top-left) for about a second. A three-finger hold also works when Guided Access isn't intercepting it.
- **Exit app:** in the preset picker, this explains how to leave: triple-click the top button and enter your Guided Access passcode. iOS doesn't let a web page close itself, which is exactly what makes Guided Access a real kiosk.

## Known limits

- iOS Safari doesn't expose battery state, so the charging icon is hidden.
- Home Screen web apps may reload after long periods in the background. The dashboard recovers on its own when that happens.
