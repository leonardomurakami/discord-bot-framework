from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .config import TIMESTAMP_FORMATS


def parse_timestamp_input(time_input: str) -> int:
    """Convert a time input string into a unix timestamp."""
    time_input = time_input.strip()

    if time_input.lower() == "now":
        return int(datetime.now().timestamp())

    if time_input.isdigit():
        timestamp = int(time_input)
        if timestamp < 0 or timestamp > 4_102_444_800:  # up to 2100
            raise ValueError("Timestamp out of reasonable range")
        return timestamp

    for fmt in TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(time_input, fmt)
            return int(parsed.timestamp())
        except ValueError:
            continue

    raise ValueError("Invalid date format")


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Convert RGB values to HSL representation."""
    r_f, g_f, b_f = [channel / 255.0 for channel in (r, g, b)]
    max_val = max(r_f, g_f, b_f)
    min_val = min(r_f, g_f, b_f)
    diff = max_val - min_val

    lightness = (max_val + min_val) / 2

    if diff == 0:
        hue = saturation = 0
    else:
        saturation = diff / (2 - max_val - min_val) if lightness > 0.5 else diff / (max_val + min_val)

        if max_val == r_f:
            hue = (g_f - b_f) / diff + (6 if g_f < b_f else 0)
        elif max_val == g_f:
            hue = (b_f - r_f) / diff + 2
        else:
            hue = (r_f - g_f) / diff + 4

        hue /= 6

    return (int(hue * 360), int(saturation * 100), int(lightness * 100))


def chunk_text(text: str, limit: int) -> Iterable[str]:
    """Yield chunks of text within the provided limit."""
    for i in range(0, len(text), limit):
        yield text[i : i + limit]
