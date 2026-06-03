import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_band(raster, band_number):
    return raster.read(band_number)


def normalize(band):
    band = band.astype(np.float32)
    return (band - band.min()) / (band.max() - band.min() + 1e-10)


def save_band_preview(band, output_path, title=None):
    normalized = normalize(band)
    plt.imshow(normalized, cmap="gray")
    if title:
        plt.title(title)
    plt.axis("off")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()


def build_rgb(raster, red_band, green_band, blue_band):
    red = normalize(raster.read(red_band))
    green = normalize(raster.read(green_band))
    blue = normalize(raster.read(blue_band))
    return np.dstack((red, green, blue))


def save_rgb_preview(rgb, output_path, title=None):
    plt.imshow(rgb)
    if title:
        plt.title(title)
    plt.axis("off")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()


def calculate_band_stats(band):
    return {
        "min": float(band.min()),
        "max": float(band.max()),
        "mean": float(band.mean()),
        "std": float(band.std()),
    }


def generate_report(metadata, stats, output_path):
    lines = [
        "Image Report",
        "=" * 40,
        "",
        f"Width:  {metadata['width']}",
        f"Height: {metadata['height']}",
        f"Bands:  {metadata['bands']}",
        f"CRS:    {metadata['crs']}",
        f"Resolution: {metadata['resolution']}",
        f"Bounds: {metadata['bounds']}",
        "",
        "Band Statistics",
        "-" * 40,
    ]
    for band_num, s in stats.items():
        lines.append(f"")
        lines.append(f"Band {band_num}:")
        lines.append(f"  Min:   {s['min']:.2f}")
        lines.append(f"  Max:   {s['max']:.2f}")
        lines.append(f"  Mean:  {s['mean']:.2f}")
        lines.append(f"  Std:   {s['std']:.2f}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
