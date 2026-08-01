# desktop-buddy

A drop-in sprite desktop pal built with PySide6. Add your own PNG frames to a sprite folder, edit one JSON file, and launch your own little desktop companion.

## Features

- Transparent, frameless, always-on-top window
- Drag the toy around the desktop
- Click to trigger a reaction animation
- Random excited outbursts while idle
- Animated states plus static base/overlay layers
- Time-aware ambient states (idle, sleep, nap) that update every hour
- Right-click menu to exit
- `--sprite <name>` argument to swap sprite sets
- A separate shadow-box build with walking, running, falling, hurting, and horizontal sprite flipping

## Quick start

You need [uv](https://docs.astral.sh/uv/) installed.

```powershell
uv sync
uv run desktop-buddy
```

Run a custom sprite:

```powershell
uv run desktop-buddy --sprite my_pet
```

Run the new shadow-box build:

```powershell
uv run desktop-buddy-shadow-box
```

## Build your own pet

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for the full guide, including:

- The Create-A-Buddy Studio, an optional Gradio app for drawing frames and exporting a sprite from a browser UI
- How to draw frames and static layers by hand
- The `sprite.json` format, including `time_states`, `actor`, and shadow-box motion settings
- Testing your sprite
- Packaging a standalone Windows `.exe` with PyInstaller

### Create-A-Buddy Studio

A separate, optional app for building sprites without leaving the browser:

```powershell
uv sync --extra studio
uv run desktop-buddy-studio
```

## Project layout

```text
desktop-buddy/
├── pyproject.toml
├── uv.lock
├── BUILD_GUIDE.md
├── src/desktop_buddy/
│   ├── __init__.py
│   ├── main.py          # window, input, app loop
│   ├── shadow_box.py    # shadow-box window with horizontal movement
│   ├── sprite.py        # manifest loader + animation driver
│   ├── studio/          # optional Gradio app: Create-A-Buddy Studio
│   └── sprites/
│       └── default/     # default placeholder sprite
│           ├── sprite.json
│           ├── base.png
│           ├── overlay.png
│           ├── idle_*.png
│           ├── happy_*.png
│           ├── sleep_*.png
│           └── nap_*.png
└── README.md
```

## License

MIT
