# Build Your Own Desktop Buddy

This guide explains how to draw a sprite, hook it into `desktop-buddy`, test it, and package it as a standalone Windows executable.

## What you need

- [uv](https://docs.astral.sh/uv/) (for running and packaging)
- An image editor that exports transparent PNGs, e.g. GIMP, Aseprite, Photoshop, or Paint.NET
- (Optional) An icon file if you want a custom `.exe` icon

## 1. Design your art

Every sprite lives in its own folder under `src/desktop_buddy/sprites/`. The default folder is a good template.

### Canvas and transparency

- All frames and all static layers must share the same `width` and `height`.
- Use transparent PNGs (RGBA). The transparent areas let the desktop show through.
- The default is `128 x 128`, but you can pick anything. A larger sprite needs a more powerful machine but gives crisper art.

### Frame files

Frames are just numbered PNGs. Name them any way you like, but keep them sorted in `sprite.json`.

Typical layout for a pet with one idle and one reaction:

```text
src/desktop_buddy/sprites/my_pet/
├── sprite.json
├── base.png        # drawn behind the animated frame
├── idle_0.png      # idle frame 0
├── idle_1.png      # idle frame 1
├── idle_2.png      # idle frame 2
├── idle_3.png      # idle frame 3
├── happy_0.png     # reaction frame 0
├── happy_1.png
├── happy_2.png
├── happy_3.png
└── overlay.png     # drawn in front of the animated frame (optional)
```

### Static layers

- `base` — a non-animated layer drawn **under** the active frame. Good for shadows, ground, or a bed the pet sits on.
- `overlay` — a non-animated layer drawn **on top** of the active frame. Good for accessories, highlights, or a frame that should never move.

Both are optional. If you do not need one, leave it out of `statics`.

## 2. Write `sprite.json`

Create a `sprite.json` next to your PNGs. Here is a full annotated example:

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
    },
    "sleepy": {
      "frames": ["sleepy_0.png", "sleepy_1.png"],
      "fps": 4,
      "loop": true
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

### Field reference

| Field | Purpose |
| --- | --- |
| `name` | Friendly name for the sprite. |
| `width` | Window width and PNG width in pixels. |
| `height` | Window height and PNG height in pixels. |
| `fps` | Default frames per second for every state. |
| `default_state` | The state to return to after a non-looping state finishes and on startup. |
| `states` | Named animation states. Each state has a `frames` array and a `loop` flag. |
| `states.<name>.frames` | Ordered list of PNG filenames for that state. |
| `states.<name>.loop` | `true` to loop forever, `false` to play once then return to `default_state`. |
| `states.<name>.fps` | Optional; overrides the global `fps` for this state only. |
| `time_states` | Optional map of state name → list of hours (0–23). The pet automatically switches to that state when the hour changes. |
| `statics.base` | Optional background layer. |
| `statics.overlay` | Optional foreground layer. |
| `statics.<layer>.image` | PNG filename. |
| `statics.<layer>.x` | Horizontal offset in pixels. |
| `statics.<layer>.y` | Vertical offset in pixels. |

### Time-aware behavior

If you add `time_states` to `sprite.json`, the toy checks the current hour every 60 minutes and switches to the matching state. A missing or unmapped hour falls back to `default_state`.

Example:

```json
"time_states": {
  "sleep": [22, 23, 0, 1, 2, 3, 4, 5, 6],
  "nap": [13, 14]
}
```

With that mapping the pet sleeps from 10 PM to 6 AM, takes an afternoon nap from 1 PM to 2 PM, and stays `idle` the rest of the day. Clicking still triggers the `happy` reaction; when `happy` finishes the pet returns to the current time-based state.

## 3. Test your sprite

After dropping your PNGs and `sprite.json` into `src/desktop_buddy/sprites/my_pet/`:

```powershell
uv run desktop-buddy --sprite my_pet
```

If something is missing, the app exits with a clear error (e.g., missing `sprite.json` or a frame file it cannot find).

## 4. Package a standalone `.exe`

Install PyInstaller:

```powershell
uv pip install pyinstaller
```

Then build. The key part is `--add-data`, which tells PyInstaller to bundle the `sprites/` folder so the `.exe` can find it at runtime.

### One-file build

```powershell
uv run pyinstaller `
  --name "DesktopBuddy" `
  --windowed `
  --noconsole `
  --onefile `
  --icon "icon.ico" `
  --add-data "src/desktop_buddy/sprites;desktop_buddy/sprites" `
  src/desktop_buddy/main.py
```

The output is `dist/DesktopBuddy.exe`.

### One-folder build

If startup speed matters more than a single file, use a folder build:

```powershell
uv run pyinstaller `
  --name "DesktopBuddy" `
  --windowed `
  --noconsole `
  --icon "icon.ico" `
  --add-data "src/desktop_buddy/sprites;desktop_buddy/sprites" `
  src/desktop_buddy/main.py
```

The output is `dist/DesktopBuddy/DesktopBuddy.exe`.

## 5. Distribute

- For a one-file build, send `dist/DesktopBuddy.exe`.
- For a one-folder build, zip the entire `dist/DesktopBuddy/` folder and send that.
- Make sure the recipient uses Windows, since the PyInstaller build targets Windows.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `.exe` starts but no sprite appears | Verify you included `--add-data "src/desktop_buddy/sprites;desktop_buddy/sprites"` and that the PNGs are in the same relative layout as in `src/`. |
| PNGs do not render | Try adding `--collect-all PySide6` to the PyInstaller command. This bundles all Qt plugins but makes the `.exe` larger. |
| Command prompt flashes on launch | Add `--windowed --noconsole`. |
| Window is too big or too small | Make `width` and `height` in `sprite.json` exactly match your PNG dimensions. |
| Click does nothing | Make sure at least one state is named `happy` or change the clicked state in `src/desktop_buddy/main.py`. |

## Want to share your sprite?

Zip your `sprites/<name>/` folder. Others can drop it into their own `desktop-buddy/src/desktop_buddy/sprites/` and run:

```powershell
uv run desktop-buddy --sprite <name>
```
