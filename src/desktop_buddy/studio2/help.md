# Desktop Buddy Studio 2

## Buddy tab

- **Buddy Name** — the name used for the sprite folder and the compiled `.exe`.
- **Buddy Type** — `desktop_buddy` for the floating pet; `shadow_box` for the horizontal walking scene.
- **Add Sprites Directory** — choose a folder with one subfolder per state, for example:

  ```text
  my_pet/
  ├── idle/
  │   ├── idle_0.png
  │   └── idle_1.png
  ├── happy/
  ├── sleep/
  ├── base.png
  ├── overlay.png
  └── sprite.json
  ```

  Each state folder holds the PNG frames for that state. `base.png` and `overlay.png` are optional static layers. `sprite.json` is optional for metadata.
- **Add Icon File** — optional `.ico` file for the compiled `.exe`.
- **Save Desktop Buddy** — imports the directory and writes `sprite.json` plus the PNGs into `src/desktop_buddy/sprites/<name>/`.

## Sprites tab

- **Sprite State** — select a state to preview.
- **Sprite FPS** — frames per second for the selected state (overrides the global FPS).
- **Loop** — whether the state loops.
- **Frame / Play / Stop** — browse or play the animation.
- **Save Desktop Buddy** — rewrites `sprite.json` and PNGs after FPS/loop changes.
- **Build Desktop Buddy** — packages the buddy into a single `dist/<name>.exe` using PyInstaller.

## Notes

- All PNGs in a state should be the same size. Studio 2 will resize them to the first frame's size.
- Static layers (`base`/`overlay`) are drawn behind and in front of each animation frame.
- For `shadow_box` builds, default `actor` and `shadow_box` motion settings are added to `sprite.json`.
