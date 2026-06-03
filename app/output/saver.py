import json
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def save_raster(output_path, data, metadata, transform=None, crs=None):
    out_meta = metadata.copy()
    if data.ndim == 2:
        out_meta.update({"count": 1, "dtype": "float32"})
    if transform:
        out_meta["transform"] = transform
    if crs:
        out_meta["crs"] = crs
    with rasterio.open(output_path, "w", **out_meta) as dst:
        if data.ndim == 2:
            dst.write(data, 1)
        else:
            dst.write(data)


def save_ndvi_preview(ndvi, output_path):
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(ndvi, cmap="RdYlGn", vmin=-1, vmax=1)
    plt.colorbar(im, ax=ax, label="NDVI")
    ax.set_title("NDVI")
    ax.axis("off")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()


def save_json_report(report, output_path):
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
