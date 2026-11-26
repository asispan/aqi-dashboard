# Linux tablet (the server and the kiosk on the same device)

This is the most capable setup: the dashboard can control **screen brightness**, show **charging state**, and the **Exit app** button closes the kiosk.

Tested on a Xiaomi Mi Pad 2 running Omarchy (Arch Linux and Hyprland). Any Linux tablet or old laptop with Chromium works the same way.

```bash
git clone https://github.com/asispan/aqi-dashboard ~/aqi-dashboard
cd ~/aqi-dashboard/app && cp config.example.json config.json && $EDITOR config.json
```

In `config.json`, set the kiosk exit command so the **Exit app** button works:

```json
"kiosk": {"exit_command": "pkill -f -- --user-data-dir=$HOME/.local/share/aqi-dashboard/chromium"}
```

Then run the server as a user service and start the kiosk at login:

```bash
mkdir -p ~/.config/systemd/user
cp ~/aqi-dashboard/deploy/linux/aqi-dashboard.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now aqi-dashboard
loginctl enable-linger "$USER"
```

| Desktop | Autostart |
|---|---|
| Hyprland | `exec-once = ~/aqi-dashboard/deploy/linux/kiosk.sh` in `hyprland.conf` (or `hl.exec_once(...)` in Lua configs) |
| GNOME / KDE / XFCE | `cp deploy/linux/aqi-dashboard-kiosk.desktop ~/.config/autostart/` |
| Sway | `exec ~/aqi-dashboard/deploy/linux/kiosk.sh` in the sway config |

## Keep the screen on

- **Hyprland:** stop `hypridle`, or remove its dpms and lock listeners.
- **GNOME:** `gsettings set org.gnome.desktop.session idle-delay 0`.
- **X11:** `xset s off -dpms`.

## Brightness

The page talks to a small brightness daemon through two files:

```json
"brightness": {"type": "file", "override_file": "/run/<daemon>/override", "level_file": "/run/<daemon>/level"}
```

- `override` contains `auto` or a level from `0` to `255`; the page writes it.
- `level` contains the level currently applied; the page reads it.

For a Mi Pad 2, see [`extras/mipad2`](../../extras/mipad2). For other hardware, a daemon of about 30 lines that writes to `/sys/class/backlight/*/brightness` does the same job.
