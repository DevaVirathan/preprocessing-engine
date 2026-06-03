"""
Preprocessing Engine — Pipeline Orchestrator

Run:
  python app/main.py
"""

from pprint import pprint
from services.pipeline import PreprocessingPipeline

pipeline = PreprocessingPipeline()

result = pipeline.run(
    raster_path="data/raw/multispectral.tif",
    boundary_path="data/boundaries/field_multispectral.geojson",
    output_dir="data/output",
    red_band=3,
    nir_band=4,
    scl_band=5,
)

print("\n=== Pipeline Result ===")
pprint(result)
