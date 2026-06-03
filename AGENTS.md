# Preprocessing Engine — Agent Guide

## Build / Run Commands

```bash
source venv/bin/activate
python app/main.py                        # CLI pipeline
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # API server
```

## Project Conventions

- **Imports**: use `from app.<module>.<file> import <name>` (app-prefixed) everywhere.
- **Pipeline steps** live in `app/services/pipeline.py` as `PreprocessingPipeline` methods.
- **Per-phase scripts** are `app/main_*.py` (main_ndvi.py, main_dos.py, main_mosaic.py, main_preprocess.py).
- **Data outputs** go under `data/` with one subdirectory per phase/feature.
- **API runs** create UUID-named dirs under `data/api_outputs/`.
- **Do NOT** touch `input.txt` or modify synthetic test data without notice.

## Module Map

| Module | File | Purpose |
|---|---|---|
| ingestion | `raster_loader.py` | `rasterio.open()` |
| ingestion | `metadata.py` | `extract_metadata()`, `validate_raster()` |
| ingestion | `metadata_writer.py` | `save_metadata()` → JSON |
| visualization | `raster_visualizer.py` | normalize, RGB, previews, stats, reports |
| boundary | `boundary_loader.py` | GeoPandas read |
| boundary | `reproject.py` | CRS transform via `to_crs()` |
| preprocessing | `subset.py` | `clip_raster()` via `rasterio.mask` |
| cloud | `detector.py` | SCL + threshold cloud detection |
| cloud | `masker.py` | apply mask, NaN, stats |
| correction | `atmospheric.py` | Dark Object Subtraction |
| correction | `radiometric.py` | NoData handling, rescaling |
| quality | `validator.py` | band validation, quality report |
| validation | `validator.py` | raster/band validation |
| analytics | `ndvi.py` | `calculate_ndvi()`, save TIF/PNG |
| analytics | `statistics.py` | NDVI stats (min/max/mean/median/std) |
| analytics | `classification.py` | NDVI thresholds, health summary |
| mosaic | `merger.py` | `create_mosaic()` via `rasterio.merge` |
| mosaic | `validator.py` | tile CRS/bands/res consistency |
| output | `saver.py` | save raster, JSON, NDVI preview |
| services | `pipeline.py` | `PreprocessingPipeline.run()` orchestrator |
| api | `routes.py` | FastAPI endpoints |
| api | `schemas.py` | Pydantic models |

## Lint / Test

No lint or test command currently configured. Run `python app/main.py` for a full pipeline smoke test.
