from pprint import pprint

from ingestion.raster_loader import load_raster
from ingestion.metadata import extract_metadata, validate_raster
from ingestion.metadata_writer import save_metadata
from visualization.raster_visualizer import (
    load_band,
    save_band_preview,
    build_rgb,
    save_rgb_preview,
    calculate_band_stats,
    generate_report,
)

RASTER_PATH = "data/raw/image.tif"
METADATA_PATH = "data/metadata/metadata.json"
PREVIEW_DIR = "data/preview"
REPORT_PATH = "data/reports/image_report.txt"

raster = load_raster(RASTER_PATH)

# --- Phase 1: Info & Validation ---
print("=== Raster Info ===")
print("Width:", raster.width)
print("Height:", raster.height)
print("Bands:", raster.count)
print("CRS:", raster.crs)
print("Resolution:", raster.res)
print("Bounds:", raster.bounds)
print()

metadata = extract_metadata(raster)
print("=== Metadata Report ===")
pprint(metadata)
print()

validation_status = validate_raster(raster)
print("=== Validation ===")
print("Valid:", validation_status)
print()

# --- Phase 2: Metadata Persistence ---
save_metadata(metadata, METADATA_PATH)
print(f"Metadata saved to {METADATA_PATH}")

# --- Phase 2: Band Previews ---
for i in range(1, raster.count + 1):
    band = load_band(raster, i)
    preview_path = f"{PREVIEW_DIR}/band_{i}_preview.png"
    save_band_preview(band, preview_path, title=f"Band {i}")
    print(f"Band {i} preview saved to {preview_path}")

# --- Phase 2: RGB Composite ---
if raster.count >= 3:
    rgb = build_rgb(raster, red_band=3, green_band=2, blue_band=1)
    rgb_path = f"{PREVIEW_DIR}/rgb_preview.png"
    save_rgb_preview(rgb, rgb_path, title="RGB Composite")
    print(f"RGB preview saved to {rgb_path}")

# --- Phase 2: Band Statistics ---
stats = {}
for i in range(1, raster.count + 1):
    band = load_band(raster, i)
    stats[i] = calculate_band_stats(band)
    print(f"Band {i} stats: {stats[i]}")

# --- Phase 2: Report ---
generate_report(metadata, stats, REPORT_PATH)
print(f"Report saved to {REPORT_PATH}")

raster.close()
print("\nPhase 2 complete.")
