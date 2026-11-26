# Making a preset

A preset is a CSS file that overrides the dashboard's colour variables, plus one entry in `app/web/presets/index.json`.

```jsonc
// app/web/presets/index.json
{"id": "my-preset", "name": "My Preset", "note": "one line shown in the picker",
 "css": "my-preset.css",
 "thumbs": {"day": "thumbs/my-preset-day.jpg", "night": "thumbs/my-preset-night.jpg"}}
```

```css
/* app/web/presets/my-preset.css */
/* --bg page, --card tiles, --line borders, --ink text and big numbers, --mute labels, --accent highlights */
:root[data-theme=light]{--bg:#f3efe6;--card:#fffdf8;--line:#e3dccd;--ink:#1b1a17;--mute:#6f6a5f;--accent:#2f6f4f}
:root[data-theme=dark] {--bg:#0e1210;--card:#16201a;--line:#253128;--ink:#e8eadf;--mute:#9aa596;--accent:#9fd8a8}
/* a single-mode preset (like Sunny Meadow) can define only one of the two */
```

**Rules that keep it legible from across a room:**

- Keep a contrast ratio of at least 7:1 between `--ink` and `--card` for the two big numbers.
- Don't redefine the AQI band colours. `alerts.css` is loaded after every preset (with `!important`), so alerts always use the EPA traffic-light colours.
- Make thumbnails from real screenshots: open `/?preset=my-preset&theme=light` at 1024×768 and resize the capture to 640 px wide.

The picker re-reads `index.json` every time it opens, and the server sends `no-cache` headers, so a new preset appears on the tablet without restarting anything.
