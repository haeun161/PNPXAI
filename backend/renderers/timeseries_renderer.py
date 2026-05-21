import os
import numpy as np
import matplotlib.pyplot as plt


def render_timeseries_attribution(
    signal: np.ndarray,
    attribution: np.ndarray,
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    attr = np.abs(attribution.flatten())
    if len(attr) != len(signal):
        attr = np.interp(
            np.linspace(0, 1, len(signal)),
            np.linspace(0, 1, len(attr)),
            attr,
        )

    attr_max = attr.max()
    if attr_max > 0:
        attr = attr / attr_max

    fig, ax1 = plt.subplots(figsize=(6, 3), dpi=100)

    # Plot signal
    x = np.arange(len(signal))
    ax1.plot(x, signal, color="steelblue", linewidth=1.5, label="Signal")
    ax1.set_ylabel("Value", color="steelblue", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="steelblue")

    # Overlay attribution as filled area
    ax2 = ax1.twinx()
    ax2.fill_between(x, 0, attr, alpha=0.3, color="orangered", label="Attribution")
    ax2.set_ylabel("Attribution", color="orangered", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="orangered")
    ax2.set_ylim(0, 1.2)

    ax1.set_xlabel("Time Step", fontsize=10)
    ax1.set_title("Time-Series Attribution", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)

    return output_path
