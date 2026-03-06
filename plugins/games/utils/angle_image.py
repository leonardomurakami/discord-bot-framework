"""Generate angle game images using matplotlib."""
from __future__ import annotations

import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")  # non-interactive backend

# Discord dark theme palette
BG_COLOR = "#2b2d31"
CIRCLE_COLOR = "#5865f2"  # Discord blurple
TARGET_COLOR = "#faa61a"  # gold — the mystery ray
TEXT_COLOR = "#dcddde"
GRID_COLOR = "#40444b"


def generate_angle_image(target: int) -> bytes:
    """
    Render a protractor showing the mystery angle as an unlabeled ray.

    The user must visually estimate the angle and submit their numeric guess.

    Args:
        target: The correct angle (degrees, 0-360). Drawn without a degree label.

    Returns:
        PNG image bytes.
    """
    fig, ax = plt.subplots(figsize=(6, 6), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_aspect("equal")
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.axis("off")

    # --- outer decorative ring ---
    outer = plt.Circle((0, 0), 1.18, fill=False, color=CIRCLE_COLOR, linewidth=1.5, alpha=0.3)
    ax.add_patch(outer)

    # --- main circle ---
    main = plt.Circle((0, 0), 1.0, fill=False, color=CIRCLE_COLOR, linewidth=2.5)
    ax.add_patch(main)

    # --- degree tick marks and labels every 30° ---
    for deg in range(0, 360, 30):
        rad = np.radians(deg)
        inner_r, outer_r = 0.92, 1.0
        ax.plot(
            [inner_r * np.cos(rad), outer_r * np.cos(rad)],
            [inner_r * np.sin(rad), outer_r * np.sin(rad)],
            color=GRID_COLOR, linewidth=1.2,
        )
        label_r = 1.28
        ax.text(
            label_r * np.cos(rad),
            label_r * np.sin(rad),
            f"{deg}°",
            ha="center", va="center",
            fontsize=7, color=TEXT_COLOR, fontfamily="monospace",
        )

    # --- faint grid spokes every 90° ---
    for deg in (0, 90, 180, 270):
        rad = np.radians(deg)
        ax.plot([0, 0.9 * np.cos(rad)], [0, 0.9 * np.sin(rad)],
                color=GRID_COLOR, linewidth=0.8, linestyle="--", alpha=0.5)

    # --- reference dot at origin ---
    ax.plot(0, 0, "o", color=TEXT_COLOR, markersize=5, zorder=5)

    # --- mystery target ray (no degree label) ---
    rad = np.radians(target)
    tip_x, tip_y = 0.88 * np.cos(rad), 0.88 * np.sin(rad)
    ax.annotate(
        "",
        xy=(tip_x, tip_y),
        xytext=(0, 0),
        arrowprops=dict(
            arrowstyle="-|>",
            color=TARGET_COLOR,
            lw=2.8,
            mutation_scale=18,
        ),
        zorder=7,
    )

    # --- prompt label ---
    ax.text(
        0, -1.42,
        "What angle is this?",
        ha="center", va="center",
        fontsize=9, color=TEXT_COLOR, fontfamily="monospace",
    )

    plt.tight_layout(pad=0.2)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor=BG_COLOR, bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
