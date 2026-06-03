"""
Phase 7: Mosaic Engine

Pipeline:
  tile_left.tif  \
  tile_center.tif  >  Validate → Merge → merged.tif → Preview → Report
  tile_right.tif /
"""

import json
from pprint import pprint

from mosaic.merger import create_mosaic
from mosaic.validator import validate_tiles
from visualization.raster_visualizer import build_rgb_from_array, save_rgb_preview

TILE_DIR = "data/tiles"
OUT_DIR = "data/mosaic"
TILE_PATHS = [
    f"{TILE_DIR}/tile_left.tif",
    f"{TILE_DIR}/tile_center.tif",
    f"{TILE_DIR}/tile_right.tif",
]
MERGED_PATH = f"{OUT_DIR}/merged.tif"
PREVIEW_PATH = f"{OUT_DIR}/merged_preview.png"
REPORT_PATH = f"{OUT_DIR}/mosaic_report.json"

print("=" * 50)
print("Phase 7: Mosaic Engine")
print("=" * 50)

print("\nInput tiles:")
for p in TILE_PATHS:
    print(f"  {p}")

# --- Validate ---
print("\n1. Validating tiles...")
validation = validate_tiles(TILE_PATHS)
print(f"   Valid: {validation['valid']}")
print(f"   Same CRS: {validation['same_crs']}")
print(f"   Same bands: {validation['same_bands']}")
print(f"   Same resolution: {validation['same_resolution']}")

if not validation["valid"]:
    print("   WARNING: Tiles are not compatible for merging.")

# --- Merge ---
print("\n2. Merging tiles...")
result = create_mosaic(TILE_PATHS, MERGED_PATH)

import rasterio
with rasterio.open(MERGED_PATH) as src:
    print(f"   Merged shape: {src.count} bands x {src.height} x {src.width}")
    print(f"   CRS: {src.crs}")
    print(f"   Bounds: {src.bounds}")

    # --- Preview ---
    print("\n3. Generating preview...")
    if src.count >= 3:
        data = src.read()
        rgb = build_rgb_from_array(data, red_idx=2, green_idx=1, blue_idx=0)
        if rgb is not None:
            save_rgb_preview(rgb, PREVIEW_PATH, title="Merged Mosaic")
            print(f"   Saved: {PREVIEW_PATH}")

# --- Report ---
print("\n4. Mosaic report...")
report = {
    "input_tiles": len(TILE_PATHS),
    "tile_files": TILE_PATHS,
    "output_file": MERGED_PATH,
    "validated": validation["valid"],
    "crs": validation["crs"],
    "bands": validation["bands"],
    "tile_compatibility": {
        "same_crs": validation["same_crs"],
        "same_bands": validation["same_bands"],
        "same_resolution": validation["same_resolution"],
    },
    "status": "success",
}
with open(REPORT_PATH, "w") as f:
    json.dump(report, f, indent=4)
pprint(report)

print(f"\n{'=' * 50}")
print("Phase 7 complete.")
print(f"  {MERGED_PATH}")
print(f"  {PREVIEW_PATH}")
print(f"  {REPORT_PATH}")
print(f"{'=' * 50}")
