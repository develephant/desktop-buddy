"""PNG + sprite.json I/O and PyInstaller packaging for Desktop Buddy Studio 2."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

from .project import Studio2Project
from desktop_buddy.studio.project import SpriteProject, StateData, StaticLayer


SPRITES_ROOT = Path(__file__).resolve().parents[1] / "sprites"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


VALID_BUDDY_KINDS = ("desktop_buddy", "shadow_box")


def _project_root() -> Path:
    return PROJECT_ROOT


def _sanitize_exe_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_")
    return safe or "DesktopBuddy"


def _read_manifest(source: Path) -> dict | None:
    for name in ("sprite.json", "sprites.json"):
        manifest_path = source / name
        if manifest_path.is_file():
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def _normalize(image: Image.Image, width: int, height: int) -> Image.Image:
    image = image.convert("RGBA")
    if image.size != (width, height):
        image = image.resize((width, height), Image.NEAREST)
    return image


def _load_statics(source: Path, width: int, height: int) -> dict[str, StaticLayer]:
    statics: dict[str, StaticLayer] = {"base": StaticLayer(), "overlay": StaticLayer()}
    seen: set[str] = set()
    candidates = [
        (source / "base.png", source / "overlay.png"),
        (source / "static" / "base.png", source / "static" / "overlay.png"),
    ]
    for base_path, overlay_path in candidates:
        if "base" not in seen and base_path.is_file():
            img = _normalize(Image.open(base_path), width, height)
            statics["base"] = StaticLayer(image=img, x=0, y=0)
            seen.add("base")
        if "overlay" not in seen and overlay_path.is_file():
            img = _normalize(Image.open(overlay_path), width, height)
            statics["overlay"] = StaticLayer(image=img, x=0, y=0)
            seen.add("overlay")
    return statics


def _load_from_subdirs(source: Path, name: str) -> SpriteProject:
    states: dict[str, StateData] = {}
    width = height = 0

    for subdir in sorted(source.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith(".") or subdir.name == "static":
            continue
        pngs = sorted(subdir.glob("*.png"))
        if not pngs:
            continue
        frames = [Image.open(p).convert("RGBA") for p in pngs]
        if width == 0:
            width, height = frames[0].size
        frames = [_normalize(f, width, height) for f in frames]
        states[subdir.name] = StateData(frames=frames, loop=True)

    if not states:
        raise ValueError(f"No state folders with PNGs found in {source}")

    statics = _load_statics(source, width, height)
    default_state = "idle" if "idle" in states else next(iter(states))

    return SpriteProject(
        name=name,
        width=width,
        height=height,
        fps=8.0,
        default_state=default_state,
        states=states,
        statics=statics,
    )


def _load_from_manifest(source: Path, manifest: dict, name: str) -> tuple[SpriteProject, dict]:
    width = int(manifest.get("width", 0))
    height = int(manifest.get("height", 0))
    fps = float(manifest.get("fps", 8))
    default_state = manifest.get("default_state", "idle")
    time_states = manifest.get("time_states", {})

    states: dict[str, StateData] = {}
    for state_name, cfg in manifest.get("states", {}).items():
        frame_files = cfg.get("frames", [])
        frames = []
        for filename in frame_files:
            frame_path = source / filename
            if not frame_path.is_file():
                raise FileNotFoundError(f"Frame not found: {frame_path}")
            frames.append(Image.open(frame_path).convert("RGBA"))
        if not frames:
            continue
        if width == 0:
            width, height = frames[0].size
        frames = [_normalize(f, width, height) for f in frames]
        states[state_name] = StateData(
            frames=frames,
            fps=cfg.get("fps"),
            loop=cfg.get("loop", True),
        )

    if not states:
        raise ValueError("No valid states in sprite manifest")

    statics = _load_statics(source, width, height)

    if default_state not in states:
        default_state = next(iter(states))

    project = SpriteProject(
        name=name or manifest.get("name", source.name),
        width=width,
        height=height,
        fps=fps,
        default_state=default_state,
        time_states=time_states,
        states=states,
        statics=statics,
    )

    extras = {
        k: v
        for k, v in manifest.items()
        if k not in {"name", "width", "height", "fps", "default_state", "states", "statics", "time_states"}
    }
    return project, extras


def import_sprite_directory(
    source: str | Path,
    name: str | None = None,
    kind: str = "desktop_buddy",
) -> Studio2Project:
    """Import a sprite from a directory containing state subfolders or a sprite.json."""
    source = Path(source)
    if not source.is_dir():
        raise FileNotFoundError(f"Sprites directory not found: {source}")

    manifest = _read_manifest(source)
    if manifest:
        try:
            project, extras = _load_from_manifest(source, manifest, name or manifest.get("name", source.name))
            return Studio2Project(project, kind=kind, extras=extras)
        except (OSError, ValueError):
            pass

    project = _load_from_subdirs(source, name or source.name)
    return Studio2Project(project, kind=kind)


def save_sprite(studio: Studio2Project) -> Path:
    """Write a Studio2Project out to src/desktop_buddy/sprites/<name>/."""
    project = studio.project
    sprite_dir = SPRITES_ROOT / project.name
    sprite_dir.mkdir(parents=True, exist_ok=True)

    for state_name, state in project.states.items():
        for index, frame in enumerate(state.frames):
            frame.save(sprite_dir / f"{state_name}_{index}.png")

    for layer_name, layer in project.statics.items():
        if layer.image is not None:
            layer.image.save(sprite_dir / f"{layer_name}.png")

    manifest = project.to_manifest()
    extras = dict(studio.extras)
    if studio.kind == "shadow_box":
        if "actor" not in extras:
            extras["actor"] = _default_actor(project)
        if "shadow_box" not in extras:
            extras["shadow_box"] = _default_shadow_box_config()
    manifest.update(extras)

    with open(sprite_dir / "sprite.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    return sprite_dir


def _default_actor(project: SpriteProject) -> dict:
    x = project.width // 4
    return {
        "x": x,
        "y": max(0, project.height - 24),
        "start_facing": "right",
        "bounds": {"left": x, "right": project.width - x},
    }


def _default_shadow_box_config() -> dict:
    return {
        "walk_speed": 42.0,
        "run_speed": 90.0,
        "idle_seconds": [1.5, 4.0],
        "walk_seconds": [2.5, 5.0],
        "run_seconds": [0.9, 1.8],
    }


def _compose_frame(project: SpriteProject, frame: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", project.size, (0, 0, 0, 0))

    base = project.statics["base"]
    if base.image is not None:
        canvas.alpha_composite(base.image, (base.x, base.y))

    canvas.alpha_composite(frame, (0, 0))

    overlay = project.statics["overlay"]
    if overlay.image is not None:
        canvas.alpha_composite(overlay.image, (overlay.x, overlay.y))

    return canvas


def _save_temp(image: Image.Image, suffix: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    image.save(tmp.name)
    return Path(tmp.name)


def render_frame(studio: Studio2Project, state_name: str, frame_index: int) -> Path:
    """Render a single composited frame to a temporary PNG."""
    project = studio.project
    if state_name not in project.states:
        return _save_temp(Image.new("RGBA", project.size, (0, 0, 0, 0)), ".png")

    state = project.states[state_name]
    if not state.frames:
        return _save_temp(Image.new("RGBA", project.size, (0, 0, 0, 0)), ".png")

    frame_index = max(0, min(frame_index, len(state.frames) - 1))
    composed = _compose_frame(project, state.frames[frame_index])
    return _save_temp(composed, ".png")


def render_gif(studio: Studio2Project, state_name: str) -> str:
    """Render an animated preview GIF to a temporary path."""
    project = studio.project
    if state_name not in project.states:
        return str(render_frame(studio, state_name, 0))

    state = project.states[state_name]
    if not state.frames:
        return str(render_frame(studio, state_name, 0))

    fps = state.fps or project.fps or 8.0
    duration = max(1, int(1000 / fps))
    frames = [_compose_frame(project, f) for f in state.frames]
    loop = 0 if state.loop else 1

    tmp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
    frames[0].save(
        tmp.name,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=loop,
        disposal=2,
    )
    return tmp.name


def _write_launcher(root: Path, exe_name: str, kind: str, sprite_name: str) -> Path:
    launchers_dir = root / "build" / "studio2_launchers"
    launchers_dir.mkdir(parents=True, exist_ok=True)
    launcher = launchers_dir / f"{exe_name}_launcher.py"

    module = "desktop_buddy.shadow_box" if kind == "shadow_box" else "desktop_buddy.main"
    launcher.write_text(
        f"import sys\n"
        f"from {module} import main\n\n\n"
        f"def _run():\n"
        f"    sys.argv = [sys.argv[0], '--sprite', {sprite_name!r}]\n"
        f"    main()\n\n\n"
        f'if __name__ == "__main__":\n'
        f"    _run()\n",
        encoding="utf-8",
    )
    return launcher


def build_exe(studio: Studio2Project) -> Path:
    """Package the current buddy as a single Windows .exe."""
    save_sprite(studio)
    root = _project_root()
    exe_name = _sanitize_exe_name(studio.project.name)
    icon_path = studio.icon_path or str(root / "icon.ico")
    launcher = _write_launcher(root, exe_name, studio.kind, studio.project.name)

    sprites_dir = (root / "src" / "desktop_buddy" / "sprites").resolve()
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        exe_name,
        "--windowed",
        "--noconsole",
        "--onefile",
        "--icon",
        str(Path(icon_path).resolve()),
        "--paths",
        str((root / "src").resolve()),
        "--add-data",
        f"{sprites_dir};desktop_buddy/sprites",
        "--distpath",
        "dist",
        "--workpath",
        "build",
        "--specpath",
        "build",
        "--clean",
        str(launcher),
    ]

    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Build failed:\n{result.stdout}\n{result.stderr}")

    return root / "dist" / f"{exe_name}.exe"
