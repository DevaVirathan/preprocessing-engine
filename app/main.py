from pprint import pprint

from ingestion.raster_loader import load_raster
from ingestion.metadata import extract_metadata, validate_raster

raster = load_raster("data/raw/image.tif")

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
