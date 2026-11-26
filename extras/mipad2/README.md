# Xiaomi Mi Pad 2 (Intel Cherry Trail) on Linux: hardware notes

These apply to the original Mi Pad 2 running a mainline-kernel distro (tested on Omarchy, Arch Linux with Hyprland). Other tablets don't need any of this.

## Backlight

The PWM backlight driver does nothing on this tablet. The panel's real backlight controller is a **TI LP8556** on I²C bus 1, address `0x2c`, register `0x00`, with levels 0 to 255.

`lp855x_bl` never binds, because the firmware describes the chip under a disabled ACPI device (`XMCC0001`). So `mipad-autobright.py` writes the register directly:

```bash
sudo install -m755 mipad-autobright.py /usr/local/bin/mipad-autobright
echo i2c-dev | sudo tee /etc/modules-load.d/i2c-dev.conf
printf 'AB_LAT=<your latitude>\nAB_LON=<your longitude>\n' | sudo tee /etc/default/mipad-autobright
sudo cp mipad-autobright.service /etc/systemd/system/ && sudo systemctl enable --now mipad-autobright
```

**Behaviour:**

- Full brightness from local sunrise to sunset.
- At night it follows the ambient light sensor on a log curve, with a 30-minute twilight ramp.
- It never goes below level 8, so the screen is never black.

Point the dashboard at it:

```json
"brightness": {"type": "file", "override_file": "/run/mipad-autobright/override", "level_file": "/run/mipad-autobright/level"}
```

## Touch

The FocalTech `FTSC0001` touchscreen works with `hid-multitouch`. Its coordinates come through rotated relative to the landscape output, so map the touch device to the output with the same transform. In Hyprland:

```
input { touchdevice { transform = 3; output = <your output name> } }
```

## Display

The panel is native portrait (1536×2048). Run it in landscape with `transform 3` and scale 2. Fonts render at 1024×768 CSS pixels, which is what the dashboard layout is tuned for.

## No battery percentage

The fuel-gauge chip has no working mainline driver, so the dashboard shows charging state only.
