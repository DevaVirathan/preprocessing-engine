"""
Phase 6: Atmospheric Correction (DOS)
Focused before/after comparison of DOS correction.

Pipeline:
  multispectral.tif
    → NDVI from raw bands → ndvi_before.png
    → DOS correction (Red, NIR)
    → NDVI from corrected bands → ndvi_after.png
    → Comparison report
"""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ingestion.raster_loader import load_raster
from correction.atmospheric import dark_object_subtraction
from analytics.ndvi import calculate_ndvi, save_ndvi_preview
from visualization.raster_visualizer import save_rgb_preview, build_rgb

RASTER_PATH = "data/raw/multispectral.tif"
OUT_DIR = "data/dos"
RED_BAND = 3
NIR_BAND = 4

print("=" * 50)
print("Phase 6: Atmospheric Correction (DOS)")
print("=" * 50)

raster = load_raster(RASTER_PATH)
red_raw = raster.read(RED_BAND).astype(np.float32)
nir_raw = raster.read(NIR_BAND).astype(np.float32)

print("\n--- Before Correction ---")
print(f"Red:  min={red_raw.min()}, max={red_raw.max()}, mean={red_raw.mean():.1f}")
print(f"NIR:  min={nir_raw.min()}, max={nir_raw.max()}, mean={nir_raw.mean():.1f}")

ndvi_before = calculate_ndvi(red_raw, nir_raw)
print(f"NDVI: min={ndvi_before.min():.4f}, max={ndvi_before.max():.4f}, mean={ndvi_before.mean():.4f}")

save_ndvi_preview(ndvi_before, f"{OUT_DIR}/ndvi_before.png", title="NDVI Before Correction")
print(f"\nSaved: {OUT_DIR}/ndvi_before.png")

# --- DOS Correction ---
print("\n--- Applying DOS ---")
red_corrected, red_dark = dark_object_subtraction(red_raw)
nir_corrected, nir_dark = dark_object_subtraction(nir_raw)
print(f"Red dark pixel (1st percentile): {red_dark}")
print(f"NIR dark pixel (1st percentile): {nir_dark}")

# Save corrected GeoTIFFs
import rasterio
meta = raster.meta.copy()
meta.update({"dtype": "float32", "count": 1})
with rasterio.open(f"{OUT_DIR}/red_corrected.tif", "w", **meta) as dst:
    dst.write(red_corrected, 1)
with rasterio.open(f"{OUT_DIR}/nir_corrected.tif", "w", **meta) as dst:
    dst.write(nir_corrected, 1)
print(f"Saved: {OUT_DIR}/red_corrected.tif")
print(f"Saved: {OUT_DIR}/nir_corrected.tif")

print("\n--- After Correction ---")
print(f"Red:  min={red_corrected.min()}, max={red_corrected.max()}, mean={red_corrected.mean():.1f}")
print(f"NIR:  min={nir_corrected.min()}, max={nir_corrected.max()}, mean={nir_corrected.mean():.1f}")

ndvi_after = calculate_ndvi(red_corrected, nir_corrected)
print(f"NDVI: min={ndvi_after.min():.4f}, max={ndvi_after.max():.4f}, mean={ndvi_after.mean():.4f}")

save_ndvi_preview(ndvi_after, f"{OUT_DIR}/ndvi_after.png", title="NDVI After DOS Correction")
print(f"Saved: {OUT_DIR}/ndvi_after.png")

# --- Side-by-side comparison figure ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
im1 = ax1.imshow(ndvi_before, cmap="RdYlGn", vmin=-1, vmax=1)
ax1.set_title("NDVI Before Correction")
ax1.axis("off")
plt.colorbar(im1, ax=ax1, shrink=0.8)

im2 = ax2.imshow(ndvi_after, cmap="RdYlGn", vmin=-1, vmax=1)
ax2.set_title("NDVI After DOS Correction")
ax2.axis("off")
plt.colorbar(im2, ax=ax2, shrink=0.8)

plt.tight_layout()
plt.savefig(f"{OUT_DIR}/ndvi_comparison.png", bbox_inches="tight", dpi=150)
plt.close()
print(f"Saved: {OUT_DIR}/ndvi_comparison.png")

# --- DOS Report ---
dos_report = {
    "method": "Dark Object Subtraction (DOS)",
    "percentile": 1,
    "red_dark_pixel": round(float(red_dark), 2),
    "nir_dark_pixel": round(float(nir_dark), 2),
    "before": {
        "red_mean": round(float(red_raw.mean()), 2),
        "nir_mean": round(float(nir_raw.mean()), 2),
        "ndvi_mean": round(float(ndvi_before.mean()), 4),
    },
    "after": {
        "red_mean": round(float(red_corrected.mean()), 2),
        "nir_mean": round(float(nir_corrected.mean()), 2),
        "ndvi_mean": round(float(ndvi_after.mean()), 4),
    },
    "ndvi_change": round(float(ndvi_after.mean() - ndvi_before.mean()), 4),
    "status": "success",
}

with open(f"{OUT_DIR}/dos_report.json", "w") as f:
    json.dump(dos_report, f, indent=4)
print(f"\nSaved: {OUT_DIR}/dos_report.json")
print(json.dumps(dos_report, indent=2))

raster.close()
print(f"\n{'=' * 50}")
print("Phase 6 complete. All deliverables in data/dos/")
