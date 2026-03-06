"""Generate angle game images using matplotlib."""
from __future__ import annotations

import io

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")  # non-interactive backend

BG_COLOR = "#2b2d31"
REF_COLOR = "#ffffff"       # reference arm — white
MYSTERY_COLOR = "#faa61a"   # mystery arm — gold


def generate_angle_image(target: int) -> bytes:
    """
    Render two arrows forming the mystery angle — no degree labels anywhere.

    The reference arm points east (0°). The mystery arm points at *target*
    degrees counterclockwise. A subtle wedge fills the angle between them.

    Args:
        target: The angle to display (1–360 degrees).

    Returns:
        PNG image bytes.
    """
    fig, ax = plt.subplots(figsize=(5, 5), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_aspect("equal")
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.axis("off")

    arm_len = 1.2
    rad = np.radians(target)

    # --- reference arm (white, pointing east) ---
    ax.annotate(
        "",
        xy=(arm_len, 0),
        xytext=(0, 0),
        arrowprops=dict(
            arrowstyle="-|>",
            color=REF_COLOR,
            lw=2.5,
            mutation_scale=18,
        ),
        zorder=5,
    )

    # --- mystery arm (gold, at target angle) ---
    tx, ty = arm_len * np.cos(rad), arm_len * np.sin(rad)
    ax.annotate(
        "",
        xy=(tx, ty),
        xytext=(0, 0),
        arrowprops=dict(
            arrowstyle="-|>",
            color=MYSTERY_COLOR,
            lw=2.5,
            mutation_scale=18,
        ),
        zorder=5,
    )

    # --- subtle filled wedge to indicate the angle ---
    wedge = mpatches.Wedge(
        (0, 0), 0.35,
        theta1=0, theta2=target,
        color=MYSTERY_COLOR, alpha=0.18,
        zorder=3,
    )
    ax.add_patch(wedge)

    # --- arc edge of the wedge ---
    arc = mpatches.Arc(
        (0, 0), 0.7, 0.7,
        angle=0, theta1=0, theta2=target,
        color=MYSTERY_COLOR, linewidth=1.5, alpha=0.6,
        zorder=4,
    )
    ax.add_patch(arc)

    # --- center dot ---
    ax.plot(0, 0, "o", color=REF_COLOR, markersize=6, zorder=6)

    plt.tight_layout(pad=0.1)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor=BG_COLOR, bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
