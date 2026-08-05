"""In-memory project model for the Create-A-Buddy studio.

Mirrors the manifest shape `desktop_buddy.sprite.Sprite` loads, so a project
built here can be exported and run without any changes to the core app.
"""

from dataclasses import dataclass, field

from PIL import Image

DEFAULT_FPS = 8.0
VALID_SIZES = (32, 64, 128, 256)


@dataclass
class StateData:
    frames: list[Image.Image] = field(default_factory=list)
    fps: float | None = None
    loop: bool = True


@dataclass
class StaticLayer:
    image: Image.Image | None = None
    x: int = 0
    y: int = 0


@dataclass
class SpriteProject:
    name: str = "my_pet"
    width: int = 128
    height: int = 128
    fps: float = DEFAULT_FPS
    default_state: str = "idle"
    buddy_type: str = "static"
    time_states: dict[str, list[int]] = field(default_factory=dict)
    states: dict[str, StateData] = field(default_factory=dict)
    statics: dict[str, StaticLayer] = field(
        default_factory=lambda: {"base": StaticLayer(), "overlay": StaticLayer()}
    )
    backgrounds: dict[str, StaticLayer] = field(
        default_factory=lambda: {"day": StaticLayer(), "night": StaticLayer()}
    )
    foreground: StaticLayer = field(default_factory=StaticLayer)
    icons: dict[str, str | None] = field(
        default_factory=lambda: {"small": None, "medium": None, "large": None}
    )

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height

    def blank_frame(self) -> Image.Image:
        return Image.new("RGBA", self.size, (0, 0, 0, 0))

    def _normalize(self, image: Image.Image) -> Image.Image:
        image = image.convert("RGBA")
        if image.size != self.size:
            image = image.resize(self.size, Image.NEAREST)
        return image

    def add_state(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("State name cannot be empty.")
        if name in self.states:
            raise ValueError(f"State '{name}' already exists.")
        self.states[name] = StateData(frames=[self.blank_frame()])
        if not self.default_state or self.default_state not in self.states:
            self.default_state = name

    def remove_state(self, name: str) -> None:
        self.states.pop(name, None)
        if self.default_state == name:
            self.default_state = next(iter(self.states), "")

    def add_frame(self, state: str, image: Image.Image | None = None) -> int:
        state_data = self.states.setdefault(state, StateData())
        frame = self._normalize(image) if image is not None else self.blank_frame()
        state_data.frames.append(frame)
        return len(state_data.frames) - 1

    def set_frame(self, state: str, index: int, image: Image.Image) -> None:
        self.states[state].frames[index] = self._normalize(image)

    def duplicate_frame(self, state: str, index: int) -> None:
        frames = self.states[state].frames
        frames.insert(index + 1, frames[index].copy())

    def delete_frame(self, state: str, index: int) -> None:
        frames = self.states[state].frames
        if len(frames) <= 1:
            raise ValueError("A state must keep at least one frame.")
        del frames[index]

    def move_frame(self, state: str, index: int, delta: int) -> int:
        frames = self.states[state].frames
        new_index = index + delta
        if not (0 <= new_index < len(frames)):
            return index
        frames[index], frames[new_index] = frames[new_index], frames[index]
        return new_index

    def set_static(self, layer: str, image: Image.Image | None, x: int, y: int) -> None:
        self.statics[layer] = StaticLayer(
            image=self._normalize(image) if image is not None else None,
            x=x,
            y=y,
        )

    def resize_canvas(self, size: int) -> None:
        """Resize the (square) canvas and rescale every frame/static layer to match."""
        self.width = self.height = size
        for state_data in self.states.values():
            state_data.frames = [self._normalize(f) for f in state_data.frames]
        for layer in self.statics.values():
            if layer.image is not None:
                layer.image = self._normalize(layer.image)

    def to_manifest(self) -> dict:
        manifest: dict = {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "buddy_type": self.buddy_type,
            "default_state": self.default_state,
            "states": {
                state_name: {
                    "frames": [
                        f"{state_name}_{i}.png" for i in range(len(state.frames))
                    ],
                    **({"fps": state.fps} if state.fps is not None else {}),
                    "loop": state.loop,
                }
                for state_name, state in self.states.items()
            },
        }
        if self.time_states:
            manifest["time_states"] = self.time_states

        statics_manifest = {
            layer_name: {"image": f"{layer_name}.png", "x": layer.x, "y": layer.y}
            for layer_name, layer in self.statics.items()
            if layer.image is not None
        }
        if statics_manifest:
            manifest["statics"] = statics_manifest

        backgrounds_manifest = {
            bg_name: {"image": f"{bg_name}.png", "x": bg.x, "y": bg.y}
            for bg_name, bg in self.backgrounds.items()
            if bg.image is not None
        }
        if backgrounds_manifest:
            manifest["backgrounds"] = backgrounds_manifest

        if self.foreground.image is not None:
            manifest["foreground"] = {
                "image": "foreground.png",
                "x": self.foreground.x,
                "y": self.foreground.y,
            }

        icons_manifest = {
            icon_name: f"{icon_name}.png"
            for icon_name, icon_path in self.icons.items()
            if icon_path is not None
        }
        if icons_manifest:
            manifest["icons"] = icons_manifest

        return manifest
