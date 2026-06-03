"""
Phase 4: Multispectral Band Processing & NDVI Generation

Pipeline:
  multispectral.tif (+ field.geojson)
    → Band Extraction (Red, NIR)
    → NDVI Calculation
    → Export (ndvi.tif, ndvi.png)
    → Statistics
    → Health Classification
    → Report
"""

import json
from pprint import pprint

from app.ingestion.raster_loader import load_raster
from app.ingestion.metadata import extract_metadata
from app.boundary.boundary_loader import load_boundary
from app.boundary.reproject import reproject_boundary
from app.preprocessing.subset import clip_raster
from app.analytics.ndvi import calculate_ndvi, save_ndvi_raster, save_ndvi_preview
from app.analytics.statistics import calculate_ndvi_stats
from app.analytics.classification import health_summary, build_health_report

RASTER_PATH = "data/raw/multispectral.tif"
BOUNDARY_PATH = "data/boundaries/field_multispectral.geojson"
NDVI_DIR = "data/ndvi"
NDVI_TIF_PATH = f"{NDVI_DIR}/ndvi.tif"
NDVI_PNG_PATH = f"{NDVI_DIR}/ndvi.png"
STATS_PATH = f"{NDVI_DIR}/ndvi_stats.json"
HEALTH_REPORT_PATH = f"{NDVI_DIR}/health_report.json"

FIELD_ID = 1
RED_BAND = 3
NIR_BAND = 4

print("=" * 50)
print("Phase 4: NDVI Analytics Pipeline")
print("=" * 50)

# --- Load raster ---
raster = load_raster(RASTER_PATH)
print(f"\nLoaded: {RASTER_PATH}")
print(f"  Bands: {raster.count}, Size: {raster.width}x{raster.height}, CRS: {raster.crs}")

# --- Load and reproject boundary ---
boundary = load_boundary(BOUNDARY_PATH)
if str(boundary.crs) != str(raster.crs):
    print(f"  Reprojecting boundary: {boundary.crs} → {raster.crs}")
    boundary = reproject_boundary(boundary, raster.crs)

# --- Clip raster to field boundary ---
geometry = [feature for feature in boundary.geometry]
clipped, transform = clip_raster(raster, geometry)
print(f"\nClipped to field: {clipped.shape[1]}x{clipped.shape[2]} px")

# --- Extract Red and NIR bands ---
red = clipped[RED_BAND - 1]
nir = clipped[NIR_BAND - 1]
print(f"Red band:  min={red.min()}, max={red.max()}")
print(f"NIR band:  min={nir.min()}, max={nir.max()}")

# --- Calculate NDVI ---
ndvi = calculate_ndvi(red, nir)
print(f"\nNDVI computed: {ndvi.shape}")
print(f"  Range: {ndvi.min():.4f} to {ndvi.max():.4f}")
print(f"  Mean:  {ndvi.mean():.4f}")

# --- Save NDVI GeoTIFF ---
save_ndvi_raster(ndvi, raster.meta, transform, raster.crs, NDVI_TIF_PATH)
print(f"\nNDVI raster saved: {NDVI_TIF_PATH}")

# --- Save NDVI preview ---
save_ndvi_preview(ndvi, NDVI_PNG_PATH)
print(f"NDVI preview saved: {NDVI_PNG_PATH}")

# --- Statistics ---
stats = calculate_ndvi_stats(ndvi)
with open(STATS_PATH, "w") as f:
    json.dump(stats, f, indent=4)
print(f"\nNDVI statistics:")
pprint(stats)

# --- Health classification ---
summary = health_summary(ndvi)
report = build_health_report(FIELD_ID, stats, summary)
with open(HEALTH_REPORT_PATH, "w") as f:
    json.dump(report, f, indent=4)
print(f"\nHealth report:")
pprint(report)

raster.close()
print(f"\n{'=' * 50}")
print("Phase 4 complete. All outputs in data/ndvi/")
print(f"  {NDVI_TIF_PATH}")
print(f"  {NDVI_PNG_PATH}")
print(f"  {STATS_PATH}")
print(f"  {HEALTH_REPORT_PATH}")
print(f"{'=' * 50}")
