# desktop-buddy

A drop-in sprite desktop pal built with PySide6. Add your own PNG frames to a sprite folder, edit one JSON file, and launch your own little desktop companion.

## Features

- Transparent, frameless, always-on-top window
- Drag the toy around the desktop
- Click to trigger a reaction animation
- Animated states plus static base/overlay layers
- Right-click menu to exit
- `--sprite <name>` argument to swap sprite sets

## Quick start

You need [uv](https://docs.astral.sh/uv/) installed.

```powershell
# Install dependencies and create the virtual environment
uv sync

# Run the default sprite
uv run desktop-buddy

# Or run a custom sprite
uv run desktop-buddy --sprite my_pet
```

## Creating a custom sprite

1. Copy the default sprite folder:

   ```powershell
   Copy-Item -Recurse src\desktop_buddy\sprites\default src\desktop_buddy\sprites\my_pet
   ```

2. Replace the PNGs inside `src/desktop_buddy/sprites/my_pet/` with your own art.
3. Edit `src/desktop_buddy/sprites/my_pet/sprite.json` to point at your frames.
4. Run it:

   ```powershell
   uv run desktop-buddy --sprite my_pet
   ```

## `sprite.json` format

```json
{
  "name": "my_pet",
  "width": 128,
  "height": 128,
  "fps": 8,
  "default_state": "idle",
  "states": {
    "idle": {
      "frames": ["idle_0.png", "idle_1.png", "idle_2.png", "idle_3.png"],
      "loop": true
    },
    "happy": {
      "frames": ["happy_0.png", "happy_1.png", "happy_2.png", "happy_3.png"],
      "loop": false
    }
  },
  "statics": {
    "base": {
      "image": "base.png",
      "x": 0,
      "y": 0
    },
    "overlay": {
      "image": "overlay.png",
      "x": 0,
      "y": 0
    }
  }
}
```

### Notes

- All PNGs should use the dimensions given by `width` and `height`.
- The `base` layer is drawn behind the active animation frame.
- The `overlay` layer is drawn on top of the active animation frame and is optional.
- A state with `"loop": false` automatically returns to `default_state` after it finishes.
- You can override `fps` per state.

## Project layout

```
desktop-buddy/
├── pyproject.toml
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
│           └── happy_*.png
└── README.md
```

## License

MIT
