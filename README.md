# Preprocessing Engine

A lightweight remote-sensing preprocessing pipeline for Sentinel-2 satellite imagery, built as a POC for crop-monitoring platforms. Takes raw GeoTIFF + field boundary GeoJSON → delivers cleaned, analyzable rasters ready for vegetation index computation (NDVI).

## What This Project Does

```
Raw Sentinel-2 GeoTIFF  +  Field Boundary (GeoJSON)
           │                        │
           ▼                        ▼
    ┌─────────────────────────────────────────────┐
    │           Preprocessing Pipeline            │
    │                                             │
    │  1. Load & Validate        (Phase 1)        │
    │  2. Extract Metadata       (Phase 1)        │
    │  3. Visualize & Preview    (Phase 2)        │
    │  4. Reproject Boundary CRS (Phase 3)        │
    │  5. Clip to Field Polygon  (Phase 3)        │
    │  6. Cloud Detection & Mask (Phase 5)        │
    │  7. DOS Atmospheric Corr.  (Phase 5/6)      │
    │  8. Mosaic Multiple Tiles  (Phase 7)        │
    │  9. Compute NDVI           (Phase 4)        │
    │ 10. Export (GeoTIFF + PNG) (Phase 2/4)      │
    └─────────────────────────────────────────────┘
           │
           ▼
  ┌────────────────────┬────────────────────┐
  │                    │                    │
  ▼                    ▼                    ▼
ndvi.tif            ndvi.png         processing_report.json
(GeoTIFF)           (visualization)   (machine-readable)
```

## Why This Exists

### The Problem

A raw Sentinel-2 tile is ~100 km × 100 km. A farmer's field is ~1 km × 1 km.

Running NDVI on the full tile:
- Wastes CPU (10,980 × 10,980 px vs ~500 × 500 px)
- Wastes storage
- Produces incorrect results without preprocessing

### The Four Corrections

| Correction | What | Why |
|---|---|---|
| **Radiometric** | Convertraw DN to reflectance; handle NoData | Pixels are raw sensor counts, notphysical measurements |
| **Atmospheric** | Dark Object Subtraction (DOS) removes haze scattering | Atmosphere adds brightness (e.g., +200 DN), biasing NDVI by ~0.09 — enough to flip "Healthy" ↔ "Moderate" |
| **Geometric** | Reproject boundary CRS (EPSG:4326 → EPSG:32631) | Rasters are in UTM (meters); field boundaries are in WGS84 (degrees). Clipping fails without matching CRS |
| **Mosaicking** | Merge overlapping tiles with `rasterio.merge` | Large farm regions span multiple Sentinel-2 tiles; you need one continuous raster before clipping |

### Without Preprocessing

```
Raw NDVI (no correction) →  mean = 0.47  →  "Moderate"
Corrected NDVI (DOS)     →  mean = 0.56  →  "Healthy"
```

A 0.09 NDVI shift from atmospheric haze alone. Production systems cannot skip this.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        FastAPI (Phase 9)                     │
│              POST /api/v1/preprocess                         │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────┐
│              PreprocessingPipeline (Phase 8)                  │
│              app/services/pipeline.py                         │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Load &   │  │ Reproject│  │ Clip to  │  │ Cloud Mask  │  │
│  │ Validate │──►│ Boundary │──►│ Field    │──►│ (SCL band)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────┬───────┘  │
│                                                    │          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │          │
│  │ Export   │◄─│ NDVI     │◄─│ DOS      │◄────────┘          │
│  │ (TIF/PNG)│  │ Compute  │  │ Correct  │                    │
│  └──────────┘  └──────────┘  └──────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
preprocessing-engine/
│
├── app/                              # Application code
│   ├── __init__.py
│   │
│   ├── main.py                       # FastAPI entry point (uvicorn app.main:app)
│   │
│   ├── api/                          # REST API layer (Phase 9)
│   │   ├── routes.py                 #   GET /health, POST /preprocess
│   │   └── schemas.py                #   Pydantic request/response models
│   │
│   ├── ingestion/                    # Raster loading (Phase 1)
│   │   ├── raster_loader.py          #   rasterio.open() wrapper
│   │   ├── metadata.py               #   extract_metadata(), validate_raster()
│   │   └── metadata_writer.py        #   save_metadata() → JSON
│   │
│   ├── visualization/                # Preview generation (Phase 2)
│   │   └── raster_visualizer.py      #   normalize(), build_rgb(), save_preview(),
│   │                                  #   calculate_band_stats(), generate_report()
│   │
│   ├── boundary/                     # Field boundary handling (Phase 3)
│   │   ├── boundary_loader.py        #   load_boundary() via GeoPandas
│   │   └── reproject.py             #   reproject_boundary() CRS transform
│   │
│   ├── preprocessing/                # Core spatial ops (Phase 3)
│   │   └── subset.py                 #   clip_raster() via rasterio.mask
│   │
│   ├── cloud/                        # Cloud detection (Phase 5)
│   │   ├── detector.py              #   SCL-based + threshold cloud detection
│   │   └── masker.py                #   apply_cloud_mask(), compute_cloud_stats()
│   │
│   ├── correction/                   # Atmospheric correction (Phase 5/6)
│   │   ├── atmospheric.py            #   dark_object_subtraction(), dos_correct_raster()
│   │   └── radiometric.py            #   handle_nodata(), rescale_band()
│   │
│   ├── quality/                      # Quality checks (Phase 5)
│   │   └── validator.py              #   validate_band(), quality_report()
│   │
│   ├── validation/                   # Pipeline input validation (Phase 8)
│   │   └── validator.py              #   validate_raster()
│   │
│   ├── analytics/                    # Vegetation indices (Phase 4)
│   │   ├── ndvi.py                   #   calculate_ndvi(), save_ndvi_raster/preview()
│   │   ├── statistics.py             #   calculate_ndvi_stats()
│   │   └── classification.py         #   classify_ndvi(), health_summary()
│   │
│   ├── mosaic/                       # Tile merging (Phase 7)
│   │   ├── merger.py                 #   create_mosaic() via rasterio.merge
│   │   └── validator.py              #   validate_tiles() CRS/bands/res check
│   │
│   ├── output/                       # Output serialization (Phase 8)
│   │   └── saver.py                  #   save_raster(), save_ndvi_preview(), save_json()
│   │
│   └── services/                     # Pipeline orchestrator (Phase 8)
│       └── pipeline.py               #   PreprocessingPipeline.run()
│
├── data/                             # Data artifacts
│   ├── raw/                          #   Input GeoTIFFs
│   │   ├── image.tif                 #   3-band sample (B, G, R)
│   │   └── multispectral.tif         #   5-band synthetic (B, G, R, NIR, SCL)
│   │
│   ├── boundaries/                   #   Field boundary GeoJSON
│   ├── metadata/                     #   metadata.json
│   ├── preview/                      #   Band + RGB preview PNGs
│   ├── reports/                      #   image_report.txt
│   ├── clipped/                      #   field.tif + processing_report.json
│   ├── ndvi/                         #   ndvi.tif, ndvi.png, ndvi_stats.json
│   ├── dos/                          #   DOS correction outputs
│   ├── mosaic/                       #   Merged mosaic outputs
│   ├── preprocessing/                #   Preprocessing outputs
│   ├── tiles/                        #   Test tiles for mosaic
│   ├── output/                       #   Pipeline orchestrator outputs
│   └── api_outputs/                  #   API-generated outputs (per-run UUID dirs)
│
├── tests/                            # (empty — ready for tests)
├── requirements.txt
├── README.md
└── input.txt                         # Original phase-by-phase spec
```

## Phases

### Phase 1 — Raster Loader
**What:** Open a GeoTIFF, read width/height/bands/CRS/resolution/bounds, validate it's not empty.
**Why:** Every pipeline step depends on a valid raster handle. This is the entry gate.
**Key insight:** A GeoTIFF is a NumPy array with geographic metadata attached.

```
app/ingestion/
├── raster_loader.py        rasterio.open(path)
├── metadata.py             extract_metadata(), validate_raster()
└── metadata_writer.py      save_metadata() → metadata.json
```

---

### Phase 2 — Metadata & Visualization
**What:** Persist metadata as JSON, generate single-band grayscale previews, RGB composites, band statistics, and a human-readable image report.
**Why:** Production systems never re-open huge GeoTIFFs to read metadata. They store it separately. Previews allow quick visual inspection without GIS tools.
**Key files:**
```
app/visualization/
└── raster_visualizer.py    normalize(), build_rgb(), save_preview(),
                            calculate_band_stats(), generate_report()
```

---

### Phase 3 — Field Boundary & Clipping
**What:** Load a GeoJSON polygon, detect CRS mismatch (EPSG:4326 vs EPSG:32631), reproject if needed, clip the raster to the field boundary.
**Why:** A Sentinel-2 tile is 100×100 km. A field is ~1×1 km. Clipping reduces data volume by ~99% before any computation.
```
app/boundary/
├── boundary_loader.py       load_boundary() → GeoDataFrame
└── reproject.py             reproject_boundary() → to_crs()

app/preprocessing/
└── subset.py                clip_raster() via rasterio.mask.mask()
```

---

### Phase 4 — NDVI Analytics
**What:** Extract Red (B4) and NIR (B8) bands, compute NDVI = (NIR − Red) / (NIR + Red), classify every pixel (Poor < 0.2 < Moderate < 0.5 < Healthy), generate health report.
**Why:** NDVI is the most widely used vegetation index in agricultural remote sensing. It directly correlates with crop health.
**NDVI interpretation:**
| Value | Meaning |
|---|---|
| < 0.2 | Bare soil, water, or dead vegetation |
| 0.2 – 0.5 | Sparse or stressed vegetation |
| 0.5 – 0.8 | Healthy vegetation |
| > 0.8 | Very dense, vigorous vegetation |

```
app/analytics/
├── ndvi.py                  calculate_ndvi(), save_ndvi_raster/preview()
├── statistics.py            calculate_ndvi_stats()
└── classification.py        classify_ndvi(), health_summary(), build_health_report()
```

---

### Phase 5 — Preprocessing Corrections Engine
**What:** Cloud detection via SCL band, cloud masking (pixels → NaN), DOS atmospheric correction, NoData handling, quality validation.
**Why:** Clouds create false NDVI (shadow → low, cloud edge → high). Atmospheric haze adds a uniform offset that biases every pixel. These must be removed before any vegetation analysis.
```
app/cloud/
├── detector.py              detect_clouds_from_scl(), detect_clouds_threshold()
└── masker.py                apply_cloud_mask(), compute_cloud_stats()

app/correction/
├── atmospheric.py           dark_object_subtraction(), dos_correct_raster()
└── radiometric.py           handle_nodata(), rescale_band()

app/quality/
└── validator.py             validate_band(), quality_report()
```

---

### Phase 6 — Atmospheric Correction (DOS)
**What:** Dark Object Subtraction: find the 1st percentile pixel value (assumed to be a "zero-reflectance" object like deep water), subtract that offset from the entire band.
**Why:** Without DOS, NDVI is underestimated by ~0.09 for our test data — enough to change a field's classification from "Healthy" → "Moderate".
**Before vs after (our test data):**
```
              Raw          DOS-corrected    Change
Red mean:     1007         807              −200 (haze removed)
NIR mean:     2949         2849             −100
NDVI mean:    0.47         0.56             +0.09 ▲
```

---

### Phase 7 — Mosaic Engine
**What:** Validate that multiple tiles share the same CRS/bands/resolution, then merge them into one continuous raster via `rasterio.merge.merge()`.
**Why:** A large farm region or district spans multiple Sentinel-2 tiles. You need one seamless raster before clipping individual fields.
```
app/mosaic/
├── merger.py                create_mosaic() via rasterio.merge.merge()
└── validator.py             validate_tiles() — CRS/bands/res check
```

---

### Phase 8 — Pipeline Orchestrator
**What:** `PreprocessingPipeline` class with a single `run()` method that chains all 8 steps: load → validate → reproject → clip → cloud mask → DOS → NDVI → export.
**Why:** Manual step-by-step execution is error-prone and non-reproducible. An orchestrator gives you atomicity, logging, and a standard result object.
```
app/services/
└── pipeline.py              PreprocessingPipeline.run()

app/output/
└── saver.py                 save_raster(), save_ndvi_preview(), save_json_report()

app/validation/
└── validator.py             validate_raster(), validate_band()
```

**Usage:**
```python
from app.services.pipeline import PreprocessingPipeline

result = PreprocessingPipeline().run(
    raster_path="data/raw/multispectral.tif",
    boundary_path="data/boundaries/field_multispectral.geojson",
    output_dir="data/output",
)
# result = {
#   "status": "success",
#   "steps": ["load", "validate", ..., "ndvi"],
#   "ndvi_path": "data/output/ndvi.tif",
#   ...
# }
```

---

### Phase 9 — FastAPI Service Layer
**What:** REST API wrapping the pipeline. Two endpoints: `GET /api/v1/health` and `POST /api/v1/preprocess`. Auto-generated Swagger UI at `/docs`.
**Why:** Expose the pipeline as a service so frontends, dashboards, and external systems can trigger preprocessing remotely.
```
app/api/
├── routes.py                FastAPI router with /health and /preprocess
└── schemas.py               Pydantic request/response models

app/main.py                  FastAPI app entry point
```

**API reference:**
```bash
# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/api/v1/health
# → {"status": "ok"}

# Run pipeline
curl -X POST http://localhost:8000/api/v1/preprocess \
  -H "Content-Type: application/json" \
  -d '{"image": "data/raw/multispectral.tif", "boundary": "data/boundaries/field_multispectral.geojson"}'
# → {"status": "success", "output_dir": "data/api_outputs/abc123", "ndvi": "...", "steps": [...]}

# Swagger UI: http://localhost:8000/docs
```

## Quick Start

```bash
# 1. Clone and enter
cd preprocessing-engine

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run CLI pipeline
python app/main.py

# 5. Or start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Data Flow

```
Input files:              Processing steps:              Output files:
─────────────────────────────────────────────────────────────────────────
data/raw/image.tif        load_raster()                  data/metadata/metadata.json
                          extract_metadata()             data/preview/band_{1..n}_preview.png
data/raw/multispectral.tif validate_raster()              data/preview/rgb_preview.png
                          generate_report()              data/reports/image_report.txt
                                                         
data/boundaries/          load_boundary()                
  field.geojson           reproject_boundary()           
                          clip_raster()                  data/clipped/field.tif
                                                         data/ndvi/ndvi_stats.json
                          calculate_ndvi()               data/ndvi/ndvi.tif
                          classify_ndvi()                data/ndvi/ndvi.png
                                                         data/ndvi/health_report.json
                          detect_clouds()                data/preprocessing/cloud_mask.tif
                          apply_dos()                    data/preprocessing/corrected/*.tif
                                                         data/preprocessing/quality_report.json
data/tiles/*.tif          create_mosaic()                data/mosaic/merged.tif
                                                         data/mosaic/merged_preview.png
                                                         data/mosaic/mosaic_report.json

All of the above:         PreprocessingPipeline.run()   data/output/ndvi.tif
                                                         data/output/ndvi.png
                                                         data/output/processing_report.json

Via API:                  POST /api/v1/preprocess       data/api_outputs/{run_id}/*
```

## Requirements

```
rasterio          — GeoTIFF I/O
numpy             — Array math
matplotlib        — Preview images
geopandas         — Vector boundary I/O
shapely           — Geometry ops
fastapi           — REST API
uvicorn           — ASGI server
pydantic          — Request/response schemas
```

## Output Interpretation

### NDVI values

```
-1.0  ─── 0.0  ─── 0.2  ─── 0.5  ─── 0.8  ─── 1.0
  │        │        │        │        │        │
 Water   Bare    Stressed Moderate Healthy  Dense
         soil    /poor                    canopy
```

### Health classification (from our test run)

```
Healthy:   74.9%   ← NDVI ≥ 0.5
Moderate:  16.5%   ← 0.2 ≤ NDVI < 0.5
Poor:       8.6%   ← NDVI < 0.2

Overall: Healthy  (mean NDVI = 0.51)
```

## What Commercial Platforms Do Differently

| This POC | Production system |
|---|---|
| Local files | PostGIS / Cloud storage (S3, Blob) |
| Synchoronous API | Async job queue (Celery, Airflow) |
| Simple DOS | Sen2Cor, 6S, FLAASH |
| SCL-band cloud mask | Multi-temporal cloud detection, Fmask |
| Single-date NDVI | Time-series NDVI (10+ years) |
| No tile server | COG + TiTiler + MapTiler |
| Synthetic test data | Real Sentinel-2 from Copernicus Data Space |

## License

This is a learning POC. Data samples may be subject to Copernicus Sentinel data terms (CC BY 4.0 where applicable).
