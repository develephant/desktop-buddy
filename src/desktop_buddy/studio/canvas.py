"""Helpers for bridging gr.ImageEditor values and stored sprite frames."""

from typing import Any

import numpy as np
from PIL import Image


def blank_canvas(size: int) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def editor_value_to_image(value: Any, size: int) -> Image.Image:
    """Extract the composited layer from a gr.ImageEditor value and normalize
    it to an RGBA square of `size` x `size`, nearest-neighbor scaled so
    pixel-art edges stay crisp when downscaling from the editor's working
    resolution.
    """
    if value is None:
        return blank_canvas(size)

    composite = value.get("composite") if isinstance(value, dict) else value
    if composite is None:
        return blank_canvas(size)

    if isinstance(composite, np.ndarray):
        image = Image.fromarray(composite)
    elif isinstance(composite, Image.Image):
        image = composite
    else:
        image = Image.open(composite)

    image = image.convert("RGBA")
    if image.size != (size, size):
        image = image.resize((size, size), Image.NEAREST)
    return image


def image_to_editor_value(image: Image.Image, editor_size: int) -> Image.Image:
    """Upscale a stored (often small) frame to the editor's working canvas
    size for easier, crisper freehand editing.
    """
    if image.size == (editor_size, editor_size):
        return image
    return image.resize((editor_size, editor_size), Image.NEAREST)
