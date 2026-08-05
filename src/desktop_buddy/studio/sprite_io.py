"""PNG + sprite.json I/O for the Create-A-Buddy studio."""

import io
import json
import zipfile
from pathlib import Path

from PIL import Image

from .project import SpriteProject, StateData, StaticLayer

SPRITES_ROOT = Path(__file__).resolve().parents[1] / "sprites"


def list_sprites() -> list[str]:
    if not SPRITES_ROOT.is_dir():
        return []
    return sorted(
        p.name
        for p in SPRITES_ROOT.iterdir()
        if p.is_dir() and (p / "sprite.json").is_file()
    )


def load_sprite(name: str) -> SpriteProject:
    sprite_dir = SPRITES_ROOT / name
    manifest_path = sprite_dir / "sprite.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    project = SpriteProject(
        name=manifest.get("name", name),
        width=int(manifest.get("width", 128)),
        height=int(manifest.get("height", 128)),
        fps=float(manifest.get("fps", 8)),
        buddy_type=manifest.get("buddy_type", "static"),
        default_state=manifest.get("default_state", "idle"),
        time_states=manifest.get("time_states", {}),
        states={},
        statics={"base": StaticLayer(), "overlay": StaticLayer()},
        backgrounds={"day": StaticLayer(), "night": StaticLayer()},
        foreground=StaticLayer(),
        icons={"small": None, "medium": None, "large": None},
    )

    for state_name, state_cfg in manifest.get("states", {}).items():
        frame_files = state_cfg.get("frames", [])
        frames = [
            Image.open(sprite_dir / filename).convert("RGBA")
            for filename in frame_files
        ]
        if not frames:
            continue
        project.states[state_name] = StateData(
            frames=frames,
            fps=state_cfg.get("fps"),
            loop=bool(state_cfg.get("loop", True)),
        )

    for layer_name in ("base", "overlay"):
        cfg = manifest.get("statics", {}).get(layer_name)
        if cfg and cfg.get("image"):
            image_path = sprite_dir / cfg["image"]
            if image_path.is_file():
                project.statics[layer_name] = StaticLayer(
                    image=Image.open(image_path).convert("RGBA"),
                    x=int(cfg.get("x", 0)),
                    y=int(cfg.get("y", 0)),
                )

    for bg_name in ("day", "night"):
        cfg = manifest.get("backgrounds", {}).get(bg_name)
        if cfg and cfg.get("image"):
            image_path = sprite_dir / cfg["image"]
            if image_path.is_file():
                project.backgrounds[bg_name] = StaticLayer(
                    image=Image.open(image_path).convert("RGBA"),
                    x=int(cfg.get("x", 0)),
                    y=int(cfg.get("y", 0)),
                )

    fg_cfg = manifest.get("foreground")
    if fg_cfg and fg_cfg.get("image"):
        image_path = sprite_dir / fg_cfg["image"]
        if image_path.is_file():
            project.foreground = StaticLayer(
                image=Image.open(image_path).convert("RGBA"),
                x=int(fg_cfg.get("x", 0)),
                y=int(fg_cfg.get("y", 0)),
            )

    for icon_name in ("small", "medium", "large"):
        icon_filename = manifest.get("icons", {}).get(icon_name)
        if icon_filename:
            icon_path = sprite_dir / icon_filename
            if icon_path.is_file():
                project.icons[icon_name] = str(icon_path)

    if not project.states:
        raise ValueError("Sprite manifest has no valid animation states.")

    return project


def export_sprite(project: SpriteProject, target_dir: Path | None = None) -> Path:
    """Write PNG frames + sprite.json for `project` into sprites/<name>/ (or `target_dir`)."""
    if not project.states:
        raise ValueError("Add at least one state with a frame before exporting.")

    sprite_dir = target_dir if target_dir is not None else SPRITES_ROOT / project.name
    sprite_dir.mkdir(parents=True, exist_ok=True)

    manifest = project.to_manifest()

    for state_name, state in project.states.items():
        for index, frame in enumerate(state.frames):
            frame.save(sprite_dir / f"{state_name}_{index}.png")

    for layer_name, layer in project.statics.items():
        if layer.image is not None:
            layer.image.save(sprite_dir / f"{layer_name}.png")

    for bg_name, bg in project.backgrounds.items():
        if bg.image is not None:
            bg.image.save(sprite_dir / f"{bg_name}.png")

    if project.foreground.image is not None:
        project.foreground.image.save(sprite_dir / "foreground.png")

    for icon_name, icon_path in project.icons.items():
        if icon_path is not None:
            icon_src = Path(icon_path)
            if icon_src.is_file():
                icon_dst = sprite_dir / f"{icon_name}.png"
                icon_src_img = Image.open(icon_src).convert("RGBA")
                icon_src_img.save(icon_dst)

    manifest_path = sprite_dir / "sprite.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    return sprite_dir


def export_zip(project: SpriteProject) -> bytes:
    """Package the project as an in-memory zip (PNGs + sprite.json) for download."""
    if not project.states:
        raise ValueError("Add at least one state with a frame before exporting.")

    manifest = project.to_manifest()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for state_name, state in project.states.items():
            for index, frame in enumerate(state.frames):
                frame_buf = io.BytesIO()
                frame.save(frame_buf, format="PNG")
                zf.writestr(f"{state_name}_{index}.png", frame_buf.getvalue())
        for layer_name, layer in project.statics.items():
            if layer.image is not None:
                layer_buf = io.BytesIO()
                layer.image.save(layer_buf, format="PNG")
                zf.writestr(f"{layer_name}.png", layer_buf.getvalue())
        for bg_name, bg in project.backgrounds.items():
            if bg.image is not None:
                bg_buf = io.BytesIO()
                bg.image.save(bg_buf, format="PNG")
                zf.writestr(f"{bg_name}.png", bg_buf.getvalue())
        if project.foreground.image is not None:
            fg_buf = io.BytesIO()
            project.foreground.image.save(fg_buf, format="PNG")
            zf.writestr("foreground.png", fg_buf.getvalue())
        for icon_name, icon_path in project.icons.items():
            if icon_path is not None:
                icon_src = Path(icon_path)
                if icon_src.is_file():
                    icon_buf = io.BytesIO()
                    icon_img = Image.open(icon_src).convert("RGBA")
                    icon_img.save(icon_buf, format="PNG")
                    zf.writestr(f"{icon_name}.png", icon_buf.getvalue())
        zf.writestr("sprite.json", json.dumps(manifest, indent=2) + "\n")

    return buffer.getvalue()


def auto_detect_states(folder_path: Path | str) -> list[str]:
    """Scan a folder for state subfolders (walk/, idle/, happy/, etc.).
    
    Returns a sorted list of state names found.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return []
    
    states = []
    for item in folder.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            png_files = list(item.glob("*.png")) + list(item.glob("*.PNG"))
            if png_files:
                states.append(item.name)
    
    return sorted(states)


def import_from_folder(project: SpriteProject, folder_path: Path | str) -> dict[str, int]:
    """Load animation frames from organized subfolders into project.states.
    
    Expects structure like:
        /path/to/assets/
            idle/
                frame_0.png
                frame_1.png
                ...
            walk/
                frame_0.png
                frame_1.png
                ...
    
    Returns a dict mapping state_name -> frame_count loaded.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"Folder not found: {folder}")
    
    results = {}
    
    for state_folder in sorted(folder.iterdir()):
        if not state_folder.is_dir() or state_folder.name.startswith("."):
            continue
        
        png_files = sorted(state_folder.glob("*.png")) + sorted(state_folder.glob("*.PNG"))
        if not png_files:
            continue
        
        state_name = state_folder.name
        frames = []
        
        for png_file in png_files:
            try:
                img = Image.open(png_file).convert("RGBA")
                img = project._normalize(img)
                frames.append(img)
            except Exception as exc:
                raise ValueError(f"Failed to load {png_file}: {exc}")
        
        if frames:
            project.states[state_name] = StateData(frames=frames)
            results[state_name] = len(frames)
            if not project.default_state or project.default_state not in project.states:
                project.default_state = state_name
    
    if not project.states:
        raise ValueError("No PNG files found in any state subfolders.")
    
    return results
