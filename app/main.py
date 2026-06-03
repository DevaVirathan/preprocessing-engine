from pprint import pprint

from ingestion.raster_loader import load_raster
from ingestion.metadata import extract_metadata, validate_raster
from ingestion.metadata_writer import save_metadata
from visualization.raster_visualizer import (
    load_band,
    save_band_preview,
    build_rgb,
    build_rgb_from_array,
    save_rgb_preview,
    calculate_band_stats,
    generate_report,
)
from boundary.boundary_loader import load_boundary
from boundary.reproject import reproject_boundary
from preprocessing.subset import (
    clip_raster,
    save_clipped_raster,
    build_processing_report,
    save_processing_report,
)

RASTER_PATH = "data/raw/image.tif"
METADATA_PATH = "data/metadata/metadata.json"
PREVIEW_DIR = "data/preview"
REPORT_PATH = "data/reports/image_report.txt"
BOUNDARY_PATH = "data/boundaries/field.geojson"
CLIPPED_PATH = "data/clipped/field.tif"
CLIPPED_PREVIEW_PATH = f"{PREVIEW_DIR}/field_preview.png"
PROCESSING_REPORT_PATH = "data/clipped/processing_report.json"

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

# --- Phase 3: Boundary Loading ---
print("\n=== Phase 3: Field Boundary Processing ===")
boundary = load_boundary(BOUNDARY_PATH)
print("Boundary loaded:")
print(boundary)
print(f"Boundary CRS: {boundary.crs}")
print(f"Boundary valid: {boundary.is_valid.all()}")
print(f"Boundary empty: {boundary.empty}")
print(f"Boundary bounds: {boundary.total_bounds}")

# --- Phase 3: CRS Reprojection ---
if str(boundary.crs) != str(raster.crs):
    print(f"CRS mismatch detected: boundary={boundary.crs}, raster={raster.crs}")
    print("Reprojecting boundary to raster CRS...")
    boundary = reproject_boundary(boundary, raster.crs)
    print(f"Boundary CRS after reprojection: {boundary.crs}")
else:
    print("CRS match: no reprojection needed.")

# --- Phase 3: Clip ---
print("Clipping raster to boundary...")
geometry = [feature for feature in boundary.geometry]
clipped, transform = clip_raster(raster, geometry)
print(f"Clipped shape: {clipped.shape}")

# --- Phase 3: Save Clipped ---
save_clipped_raster(clipped, transform, raster.meta, CLIPPED_PATH, raster.crs)
print(f"Clipped raster saved to {CLIPPED_PATH}")

# --- Phase 3: Clipped Preview ---
clipped_rgb = build_rgb_from_array(clipped)
if clipped_rgb is not None:
    save_rgb_preview(clipped_rgb, CLIPPED_PREVIEW_PATH, title="Clipped Field")
    print(f"Clipped preview saved to {CLIPPED_PREVIEW_PATH}")

# --- Phase 3: Processing Report ---
_, h, w = clipped.shape
report = build_processing_report(
    1, metadata, (h, w), raster.crs
)
save_processing_report(report, PROCESSING_REPORT_PATH)
pprint(report)

raster.close()
print("\nPhase 3 complete.")
