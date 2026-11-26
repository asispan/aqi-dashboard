#!/usr/bin/env bash
# Full-screen Chromium kiosk for the dashboard (Linux tablets, Wayland or X11).
# Kills any previous kiosk window first so relaunching never stacks windows.
URL="${AQI_DASH_URL:-http://127.0.0.1:8787/}"
PROFILE="$HOME/.local/share/aqi-dashboard/chromium"
pkill -f -- "--user-data-dir=$PROFILE" && sleep 2
mkdir -p "$PROFILE"
BROWSER="$(command -v chromium || command -v chromium-browser || command -v google-chrome-stable)"
exec "$BROWSER" --user-data-dir="$PROFILE" --app="$URL" --kiosk \
  --noerrdialogs --disable-infobars --no-first-run --disable-session-crashed-bubble \
  --disable-features=TranslateUI --check-for-update-interval=31536000 \
  --overscroll-history-navigation=0 --disable-pinch \
  ${AQI_DASH_CHROMIUM_FLAGS:-}
