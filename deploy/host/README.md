# Run the server on another always-on machine (for iPad and Android)

iPads can't run a Python server, so the server runs on any always-on computer on the same network: a Raspberry Pi, a NAS, a Mac mini or a home server. The tablet just opens `http://<host-ip>:8787/`.

```bash
git clone https://github.com/asispan/aqi-dashboard && cd aqi-dashboard/app
cp config.example.json config.json   # set monitor.url, home_name, location
python3 server.py                    # check it works: open http://<host-ip>:8787/
```

## Keep it running

**Linux (systemd):**

```bash
sudo cp ../deploy/host/aqi-dashboard-host.service /etc/systemd/system/
sudo sed -i "s#/opt/aqi-dashboard#$(cd .. && pwd)#; s#User=pi#User=$USER#" /etc/systemd/system/aqi-dashboard-host.service
sudo systemctl daemon-reload && sudo systemctl enable --now aqi-dashboard-host
```

**macOS (launchd):**

```bash
sed "s#/opt/aqi-dashboard#$(cd .. && pwd)#" ../deploy/host/com.aqi-dashboard.plist > ~/Library/LaunchAgents/com.aqi-dashboard.plist
launchctl load -w ~/Library/LaunchAgents/com.aqi-dashboard.plist
```

## Things to check

- **Give the host a fixed IP** (a DHCP reservation on your router) so the tablet's bookmark never breaks.
- **Allow port 8787** in the host's firewall, for the local network only. Don't expose it to the internet.
- **Brightness and Exit app** are tablet-side features. In this setup they come from Fully Kiosk on Android, and from Guided Access and the iPad's own settings on iPad.
