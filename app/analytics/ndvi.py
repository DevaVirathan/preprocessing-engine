import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def calculate_ndvi(red, nir):
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)
    denominator = nir + red
    denominator[denominator == 0] = 0.0001
    ndvi = (nir - red) / denominator
    return ndvi


def save_ndvi_raster(ndvi, metadata, transform, crs, output_path):
    out_meta = metadata.copy()
    out_meta.update({
        "dtype": "float32",
        "count": 1,
        "transform": transform,
        "crs": crs,
    })
    import rasterio
    with rasterio.open(output_path, "w", **out_meta) as dst:
        dst.write(ndvi, 1)


def save_ndvi_preview(ndvi, output_path, title="NDVI"):
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(ndvi, cmap="RdYlGn", vmin=-1, vmax=1)
    plt.colorbar(im, ax=ax, label="NDVI")
    ax.set_title(title)
    ax.axis("off")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
