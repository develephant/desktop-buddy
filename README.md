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

## Build your own pet

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for the full guide, including:

- How to draw frames and static layers
- The `sprite.json` format, including `time_states`
- Testing your sprite
- Packaging a standalone Windows `.exe` with PyInstaller

## Project layout

```text
desktop-buddy/
├── pyproject.toml
├── uv.lock
├── BUILD_GUIDE.md
├── src/desktop_buddy/
│   ├── __init__.py
│   ├── main.py          # window, input, app loop
│   ├── sprite.py        # manifest loader + animation driver
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
