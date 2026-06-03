"""
Phase 5: Preprocessing Corrections Engine

Pipeline:
  multispectral.tif
    → Cloud Detection (SCL)
    → Cloud Masking
    → Atmospheric Correction (DOS)
    → Validation
    → Export corrected bands & quality report
    → NDVI (from corrected bands)
"""

import json
import numpy as np
from pprint import pprint

from app.ingestion.raster_loader import load_raster
from app.cloud.detector import detect_clouds_from_scl
from app.cloud.masker import apply_cloud_mask, compute_cloud_stats
from app.correction.atmospheric import dos_correct_raster
from app.quality.validator import validate_raster, quality_report
from app.analytics.ndvi import calculate_ndvi, save_ndvi_raster, save_ndvi_preview

RASTER_PATH = "data/raw/multispectral.tif"
SCL_BAND = 5
RED_BAND_IDX = 2   # 0-based: band 3
NIR_BAND_IDX = 3   # 0-based: band 4
OUT_DIR = "data/preprocessing"

import os
os.makedirs(f"{OUT_DIR}/corrected", exist_ok=True)
os.makedirs(f"{OUT_DIR}/ndvi", exist_ok=True)

print("=" * 55)
print("Phase 5: Preprocessing Corrections Engine")
print("=" * 55)

# --- Load ---
raster = load_raster(RASTER_PATH)
data = raster.read()
meta = raster.meta
print(f"\nLoaded: {RASTER_PATH}")
print(f"  Shape (bands, h, w): {data.shape}")
print(f"  CRS: {raster.crs}")

# --- Validate ---
validate_raster(data, expected_bands=5)
print("  Validation: OK")

# --- 1. Cloud Detection (SCL) ---
scl = data[SCL_BAND - 1]
cloud_mask = detect_clouds_from_scl(scl)
cloud_stats = compute_cloud_stats(cloud_mask)
print(f"\n1. Cloud Detection:")
print(f"   Clouds: {cloud_stats['cloud_pixels']} px ({cloud_stats['cloud_percentage']}%)")

# Save cloud mask
cloud_mask_uint8 = cloud_mask.astype(np.uint8) * 255
out_meta = meta.copy()
out_meta.update({"count": 1, "dtype": "uint8"})
import rasterio
with rasterio.open(f"{OUT_DIR}/cloud_mask.tif", "w", **out_meta) as dst:
    dst.write(cloud_mask_uint8, 1)
print(f"   Saved: {OUT_DIR}/cloud_mask.tif")

# --- 2. Cloud Masking ---
print(f"\n2. Cloud Masking:")
masked = data.astype(np.float32).copy()
for i in range(4):  # skip SCL band
    masked[i] = apply_cloud_mask(data[i], cloud_mask)
# Count NaN after masking
nan_count = int(np.sum(np.isnan(masked[0])))
print(f"   NaN pixels after masking: {nan_count}")

# --- 3. Atmospheric Correction (DOS) ---
print(f"\n3. Atmospheric Correction (DOS):")
# Correct Red and NIR bands (0-based: 2, 3)
corrected_indices = [RED_BAND_IDX, NIR_BAND_IDX]
corrected, dark_values = dos_correct_raster(masked, corrected_indices, percentile=1)
for k, v in dark_values.items():
    print(f"   {k}: dark value = {v}")

# --- 4. Export corrected bands ---
print(f"\n4. Exporting corrected bands:")
out_meta = meta.copy()
out_meta.update({"dtype": "float32", "count": 1})
band_names = {2: "Red", 3: "NIR"}
for idx in corrected_indices:
    path = f"{OUT_DIR}/corrected/corrected_{band_names[idx].lower()}.tif"
    with rasterio.open(path, "w", **out_meta) as dst:
        dst.write(corrected[idx], 1)
    print(f"   Saved: {path}")

# --- 5. Quality Report ---
corrections = ["cloud_masking", "dos_atmospheric_correction"]
report = quality_report(cloud_stats, dark_values, corrections)
with open(f"{OUT_DIR}/quality_report.json", "w") as f:
    json.dump(report, f, indent=4)
print(f"\n5. Quality Report:")
pprint(report)

# --- 6. NDVI from corrected bands ---
red_corrected = corrected[RED_BAND_IDX]
nir_corrected = corrected[NIR_BAND_IDX]

# Handle NaN for NDVI calc
red_filled = np.nan_to_num(red_corrected, nan=0)
nir_filled = np.nan_to_num(nir_corrected, nan=0)

ndvi = calculate_ndvi(red_filled, nir_filled)
# Re-apply cloud mask on NDVI
ndvi[cloud_mask] = np.nan

print(f"\n6. NDVI (from corrected bands):")
print(f"   Shape: {ndvi.shape}")
valid_ndvi = ndvi[~np.isnan(ndvi)]
if len(valid_ndvi) > 0:
    print(f"   Range: {valid_ndvi.min():.4f} to {valid_ndvi.max():.4f}")
    print(f"   Mean:  {valid_ndvi.mean():.4f}")

ndvi_meta = meta.copy()
ndvi_meta.update({"dtype": "float32", "count": 1})
save_ndvi_raster(ndvi, meta, raster.transform, raster.crs, f"{OUT_DIR}/ndvi/ndvi.tif")
save_ndvi_preview(ndvi, f"{OUT_DIR}/ndvi/ndvi.png")
print(f"   Saved: {OUT_DIR}/ndvi/ndvi.tif")
print(f"   Saved: {OUT_DIR}/ndvi/ndvi.png")

raster.close()
print(f"\n{'=' * 55}")
print("Phase 5 complete.")
print(f"  {OUT_DIR}/cloud_mask.tif")
print(f"  {OUT_DIR}/corrected/corrected_red.tif")
print(f"  {OUT_DIR}/corrected/corrected_nir.tif")
print(f"  {OUT_DIR}/quality_report.json")
print(f"  {OUT_DIR}/ndvi/ndvi.tif")
print(f"  {OUT_DIR}/ndvi/ndvi.png")
print(f"{'=' * 55}")
