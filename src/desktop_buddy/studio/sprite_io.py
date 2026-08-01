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
        default_state=manifest.get("default_state", "idle"),
        time_states=manifest.get("time_states", {}),
        states={},
        statics={"base": StaticLayer(), "overlay": StaticLayer()},
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
        zf.writestr("sprite.json", json.dumps(manifest, indent=2) + "\n")

    return buffer.getvalue()
