from dataclasses import dataclass, field

from desktop_buddy.studio.project import SpriteProject


@dataclass
class Studio2Project:
    """Wrapper around a SpriteProject for Studio 2 packaging flow."""

    project: SpriteProject
    kind: str = "desktop_buddy"
    icon_path: str | None = None
    extras: dict = field(default_factory=dict)
