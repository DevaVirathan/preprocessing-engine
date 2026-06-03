# Execution Flow — Step by Step

This document traces the exact code path from entry point to output for every way you can run the engine. Use it to understand the call stack, track data transformations, and debug failures.

---

## Entry Points

There are 3 entry points into the engine:

| # | Command | Invokes | Best for |
|---|---|---|---|
| 1 | `python app/main.py` | FastAPI `app.main` `__main__` block | Quick smoke test |
| 2 | `uvicorn app.main:app` | FastAPI server → `POST /preprocess` → `PreprocessingPipeline.run()` | API usage |
| 3 | `python app/main_*.py` | Standalone phase scripts | Debugging a single phase |

---

## Entry Point 1: CLI via `python app/main.py`

**File:** `app/main.py` → `if __name__ == "__main__":` block (line 31–33)

```
app/main.py:31  if __name__ == "__main__":
app/main.py:32      import uvicorn
app/main.py:33      uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

This starts the FastAPI development server. It does **not** run the pipeline directly. Use `uvicorn app.main:app` instead (entry point 2).

---

## Entry Point 2: API via `uvicorn app.main:app`

### 2a. Server startup

```
uvicorn imports app.main:app

app/main.py:11  from fastapi import FastAPI
app/main.py:12  from fastapi.middleware.cors import CORSMiddleware
app/main.py:13  from app.api.routes import router          # ← triggers routes.py import
app/main.py:15  app = FastAPI(title="Preprocessing Engine API", ...)
app/main.py:21  app.add_middleware(CORSMiddleware, ...)
app/main.py:29  app.include_router(router, prefix="/api/v1")

── cascading imports ──

app/api/routes.py:4   from app.api.schemas import PreprocessRequest, PreprocessResponse
app/api/routes.py:5   from app.services.pipeline import PreprocessingPipeline

    └── app/services/pipeline.py:5  from app.ingestion.raster_loader import load_raster
    └── app/services/pipeline.py:6  from app.ingestion.metadata import extract_metadata
    └── app/services/pipeline.py:7  from app.boundary.boundary_loader import load_boundary
    └── app/services/pipeline.py:8  from app.boundary.reproject import reproject_boundary
    └── app/services/pipeline.py:9  from app.preprocessing.subset import clip_raster
    └── app/services/pipeline.py:10 from app.correction.atmospheric import dark_object_subtraction
    └── app/services/pipeline.py:11 from app.analytics.ndvi import calculate_ndvi
    └── app/services/pipeline.py:12 from app.output.saver import save_raster, save_ndvi_preview, save_json_report

app/api/routes.py:10  pipeline = PreprocessingPipeline()    # ← creates pipeline instance

Server is now listening on http://0.0.0.0:8000
```

### 2b. `GET /api/v1/health`

```
Request:  GET http://localhost:8000/api/v1/health

api/routes.py:13  @router.get("/health")
api/routes.py:14  def health():
api/routes.py:15      return {"status": "ok"}

Response: {"status": "ok"}
```

### 2c. `POST /api/v1/preprocess` — Full pipeline execution

This is the main execution path. Below is every function call in order.

```
── REQUEST ──
POST /api/v1/preprocess
Body:  {"image": "data/raw/multispectral.tif", "boundary": "data/boundaries/field_multispectral.geojson"}

── STEP 0: ROUTE VALIDATION ──

File: app/api/routes.py:18-39

api/routes.py:19  def preprocess(request: PreprocessRequest):
                      # request.image = "data/raw/multispectral.tif"
                      # request.boundary = "data/boundaries/field_multispectral.geojson"

api/routes.py:23  if not os.path.exists(image_path):
                      #  RAISES HTTP 400 if file missing ← DEBUG: check file path
api/routes.py:25  if not os.path.exists(boundary_path):
                      #  RAISES HTTP 400 if file missing ← DEBUG: check file path

api/routes.py:28  run_id = uuid.uuid4().hex[:8]         # e.g. "a1b2c3d4"
api/routes.py:29  output_dir = f"data/api_outputs/{run_id}"   # e.g. "data/api_outputs/a1b2c3d4"
api/routes.py:30  os.makedirs(output_dir, exist_ok=True)

api/routes.py:32  try:
api/routes.py:33      result = pipeline.run(
                          raster_path="data/raw/multispectral.tif",
                          boundary_path="data/boundaries/field_multispectral.geojson",
                          output_dir="data/api_outputs/a1b2c3d4",
                      )
api/routes.py:38  except Exception as e:
                      #  RAISES HTTP 500 with str(e) ← DEBUG: catch-all for pipeline failures
                      raise HTTPException(status_code=500, detail=str(e))

api/routes.py:41  return PreprocessResponse(
                      status="success",
                      output_dir="data/api_outputs/a1b2c3d4",
                      ndvi="data/api_outputs/a1b2c3d4/ndvi.tif",
                      steps=["load", "validate", "load_boundary", "reproject",
                             "clip", "cloud_mask", "dos_correction", "ndvi"],
                  )
```

---

## Core Pipeline: `PreprocessingPipeline.run()`

**File:** `app/services/pipeline.py:100-184`

Each step is a private method. The `run()` method chains them sequentially. If any step fails, the exception propagates up to `routes.py:38`.

### Step 1 — Load Raster

```
File: pipeline.py:109-112

pipeline.py:109  raster = self._load(raster_path)
                      #                                  ↓
                      # pipeline.py:32  def _load(self, raster_path):
                      # pipeline.py:33      logger.info("Loading raster: %s", raster_path)
                      # pipeline.py:34      return load_raster(raster_path)
                      #                                  ↓
                      # ingestion/raster_loader.py:4  def load_raster(path: str):
                      # ingestion/raster_loader.py:5      return rasterio.open(path)
                      #                                  ↓
                      # Returns: rasterio.io.DatasetReader
                      #   .count = 5 (bands)
                      #   .width = 100, .height = 100
                      #   .crs = EPSG:32631
                      #   .res = (10.0, 10.0)
                      #   .bounds = BoundingBox(left=595000, ...)

pipeline.py:111  self.results["steps"].append("load")
pipeline.py:112  metadata = extract_metadata(raster)
                      #                                  ↓
                      # ingestion/metadata.py:2  def extract_metadata(raster):
                      # ingestion/metadata.py:3-8    return {"width", "height", "bands",
                      #                              "crs", "resolution", "bounds"}
```

**Possible failures here:**
- `rasterio.errors.RasterioIOError`: File not found or corrupt GeoTIFF
- `rasterio.errors.CRSError`: Missing or invalid CRS metadata

---

### Step 2 — Validate Raster

```
File: pipeline.py:114-116

pipeline.py:115  self._validate(raster)
                      #                                  ↓
                      # pipeline.py:40  def _validate(self, raster):
                      # pipeline.py:41      from app.validation.validator import validate_raster
                      # pipeline.py:42      logger.info("Validating raster...")
                      # pipeline.py:43      validate_raster(raster)
                      #                                  ↓
                      # validation/validator.py:4  def validate_raster(raster):
                      # validation/validator.py:5      if raster.count == 0:
                      #                                    RAISES ValueError("No bands found")
                      # validation/validator.py:7      if raster.crs is None:
                      #                                    RAISES ValueError("CRS is missing")
                      # validation/validator.py:9      if raster.width == 0 or raster.height == 0:
                      #                                    RAISES ValueError("Raster has zero...")

pipeline.py:116  self.results["steps"].append("validate")
```

**Possible failures here:**
- `ValueError`: Zero bands, missing CRS, zero dimensions

---

### Step 3 — Load Boundary

```
File: pipeline.py:118-120

pipeline.py:119  boundary = self._load_boundary(boundary_path)
                      #                                  ↓
                      # pipeline.py:36  def _load_boundary(self, boundary_path):
                      # pipeline.py:37      logger.info("Loading boundary: %s", boundary_path)
                      # pipeline.py:38      return load_boundary(boundary_path)
                      #                                  ↓
                      # boundary/boundary_loader.py:4  def load_boundary(path):
                      # boundary/boundary_loader.py:5      return gpd.read_file(path)
                      #                                  ↓
                      # Returns: geopandas.GeoDataFrame
                      #   .crs = EPSG:4326
                      #   .geometry = POLYGON ((4.3956 52.2108, ...))

pipeline.py:120  self.results["steps"].append("load_boundary")
```

**Possible failures here:**
- `FileNotFoundError`: GeoJSON file missing
- `fiona.errors.DriverError`: Invalid GeoJSON format
- `ValueError`: Empty GeoDataFrame (no features)

---

### Step 4 — Reproject Boundary

```
File: pipeline.py:122-124

pipeline.py:123  boundary = self._reproject_boundary(boundary, raster.crs)
                      #                                  ↓
                      # pipeline.py:46  def _reproject_boundary(self, boundary, target_crs):
                      # pipeline.py:47      logger.info("Reprojecting boundary to %s...", target_crs)
                      # pipeline.py:48      if str(boundary.crs) != str(target_crs):
                      # pipeline.py:49          return reproject_boundary(boundary, target_crs)
                      #                                  ↓
                      # boundary/reproject.py:1  def reproject_boundary(boundary, target_crs):
                      # boundary/reproject.py:2      return boundary.to_crs(target_crs)
                      #                                  ↓
                      # Returns: geopandas.GeoDataFrame
                      #   .crs = EPSG:32631 (now matches raster)
                      #   .geometry = POLYGON ((595000 5785900, ...))
                      #
                      #   If CRS already matches: returns unchanged (line 50-51)

pipeline.py:124  self.results["steps"].append("reproject")
```

**Possible failures here:**
- `pyproj.exceptions.CRSError`: Invalid target CRS
- `ValueError`: Boundary has no CRS defined

---

### Step 5 — Clip Raster to Boundary

```
File: pipeline.py:126-128

pipeline.py:127  clipped, transform = self._clip(raster, boundary)
                      #                                  ↓
                      # pipeline.py:53  def _clip(self, raster, boundary):
                      # pipeline.py:54      logger.info("Clipping raster to boundary...")
                      # pipeline.py:55      geometry = [feature for feature in boundary.geometry]
                      # pipeline.py:56      clipped, transform = clip_raster(raster, geometry)
                      #                                  ↓
                      # preprocessing/subset.py:5  def clip_raster(raster, geometry):
                      # preprocessing/subset.py:6      clipped, transform = mask(raster, geometry, crop=True)
                      #                                  ↓
                      # Returns:
                      #   clipped:  numpy.ndarray, shape (5, 57, 40)  [bands, h, w]
                      #   transform: affine.Affine  (new geo-transform for the clipped region)

pipeline.py:128  self.results["steps"].append("clip")

Data volume change:
  Before:  100 x 100 = 10,000 pixels
  After:    57 x 40  =  2,280 pixels  ← ~77% reduction
```

**Possible failures here:**
- `rasterio.errors.WindowError`: Boundary is outside raster extent
- `ValueError`: Empty geometry list

---

### Step 6 — Cloud Mask

```
File: pipeline.py:130-132

pipeline.py:131  masked, cloud_mask = self._cloud_mask(clipped, scl_band - 1)
                      #                                  ↓
                      # pipeline.py:60  def _cloud_mask(self, data, scl_band_idx=4):
                      # pipeline.py:61      logger.info("Detecting and masking clouds...")
                      # pipeline.py:62      if data.shape[0] <= scl_band_idx:
                      #                          ← SKIP if no SCL band present (line 63-64)
                      # pipeline.py:65      from app.cloud.detector import detect_clouds_from_scl
                      # pipeline.py:66      from app.cloud.masker import apply_cloud_mask, compute_cloud_stats
                      # pipeline.py:67      scl = data[scl_band_idx]
                      # pipeline.py:68      mask = detect_clouds_from_scl(scl)
                      #                                  ↓
                      # cloud/detector.py:10  def detect_clouds_from_scl(scl_band):
                      # cloud/detector.py:11      return np.isin(scl_band, [8, 9, 10])
                      #                                  ↓
                      # Returns: numpy.ndarray(bool), shape (57, 40)
                      #   True at cloud pixel positions

                      # pipeline.py:69      stats = compute_cloud_stats(mask)
                      #                                  ↓
                      # cloud/masker.py:23  def compute_cloud_stats(cloud_mask):
                      # cloud/masker.py:24-29    return {"cloud_pixels": N, "valid_pixels": M,
                      #                                  "cloud_percentage": P}

                      # pipeline.py:71      masked = data.astype(np.float32).copy()
                      # pipeline.py:72      for i in range(data.shape[0]):
                      # pipeline.py:73          if i != scl_band_idx:
                      # pipeline.py:74              masked[i] = apply_cloud_mask(data[i], mask)
                      #                                  ↓
                      # cloud/masker.py:4   def apply_cloud_mask(band, cloud_mask):
                      # cloud/masker.py:10      band = band.astype(np.float32)
                      # cloud/masker.py:11      band[cloud_mask] = np.nan
                      # cloud/masker.py:12      return band
                      #                                  ↓
                      # Returns: masked   numpy.ndarray(float32), shape (5, 57, 40)
                      #                    Cloud pixels → NaN in bands 0-3 (SCL band skipped)

pipeline.py:132  self.results["steps"].append("cloud_mask")
```

**Possible failures here:**
- `IndexError`: `scl_band_idx` out of range (if data has fewer bands than expected)
- `MemoryError`: Large arrays on constrained hardware

---

### Step 7 — DOS Atmospheric Correction

```
File: pipeline.py:134-141

pipeline.py:135  red_idx = red_band - 1        # = 2  (0-based index for band 3)
pipeline.py:136  nir_idx = nir_band - 1        # = 3  (0-based index for band 4)

pipeline.py:137  red_corrected, nir_corrected, dos_info = self._dos_correct(
pipeline.py:138      masked[red_idx], masked[nir_idx]
                      #                                  ↓
                      # pipeline.py:77  def _dos_correct(self, red_band, nir_band):
                      # pipeline.py:78      logger.info("Applying DOS atmospheric correction...")
                      # pipeline.py:79      red_corrected, red_dark = dark_object_subtraction(red_band)
                      # pipeline.py:80      nir_corrected, nir_dark = dark_object_subtraction(nir_band)
                      #                                  ↓
                      # correction/atmospheric.py:4  def dark_object_subtraction(band, percentile=1):
                      # correction/atmospheric.py:10     band = band.astype(np.float32)
                      # correction/atmospheric.py:11     dark_value = np.percentile(band[band > 0], 1)
                      #                                  ← computes 1st percentile of non-zero pixels
                      # correction/atmospheric.py:12     corrected = band - dark_value
                      #                                  ← subtracts atmospheric offset
                      # correction/atmospheric.py:13     corrected[corrected < 0] = 0
                      #                                  ← clamps negatives to 0
                      # correction/atmospheric.py:14     return corrected, dark_value
                      #                                  ↓
                      # Returns:
                      #   red_corrected:   numpy.ndarray(float32), shape (57, 40)
                      #   nir_corrected:   numpy.ndarray(float32), shape (57, 40)
                      #   dos_info: {"red_dark_pixel": 633.86, "nir_dark_pixel": 2514.34}

pipeline.py:140  self.results["steps"].append("dos_correction")
pipeline.py:141  self.results["dos"] = dos_info
```

**Why these dark values?** The synthetic test data has a base reflectance of ~600-1500 DN (dark objects). The 1st percentile captures the darkest non-zero pixels — these represent the atmospheric scattering offset.

**Possible failures here:**
- `ZeroDivisionError`: If `band[band > 0]` is empty (all pixels are zero) — prevented by `+ 1e-10` not being in this function
- `numpy.AxisError`: If band is not 2D

---

### Step 8 — NDVI Calculation

```
File: pipeline.py:143-147

pipeline.py:144  ndvi = self._compute_ndvi(red_corrected, nir_corrected)
                      #                                  ↓
                      # pipeline.py:87  def _compute_ndvi(self, red, nir):
                      # pipeline.py:88      logger.info("Computing NDVI...")
                      # pipeline.py:89      red_filled = np.nan_to_num(red, nan=0)
                      # pipeline.py:90      nir_filled = np.nan_to_num(nir, nan=0)
                      #                                  ← replaces NaN with 0 for division stability
                      # pipeline.py:91      ndvi = calculate_ndvi(red_filled, nir_filled)
                      #                                  ↓
                      # analytics/ndvi.py:7   def calculate_ndvi(red, nir):
                      # analytics/ndvi.py:8-12    red = red.astype(np.float32)
                      #                           nir = nir.astype(np.float32)
                      #                           denom = nir + red
                      #                           denom[denom == 0] = 0.0001
                      #                           ndvi = (nir - red) / denom
                      #                           return ndvi
                      #                                  ↓
                      # Returns: numpy.ndarray(float32), shape (57, 40)
                      #          Values range from -1.0 (water) to +1.0 (dense vegetation)

pipeline.py:145  if cloud_mask is not None:
pipeline.py:146      ndvi[cloud_mask] = np.nan
                      #                     ← re-apply cloud NaN mask on NDVI

pipeline.py:147  self.results["steps"].append("ndvi")

Typical output:
  NDVI range: -0.33 to 0.87, mean: 0.56
```

**Possible failures here:**
- `FloatingPointError`: Extreme values causing overflow — unlikely with float32
- `IndexError`: Shape mismatch between ndvi and cloud_mask

---

### Step 9 — Save Outputs

```
File: pipeline.py:149-180

pipeline.py:151  os.makedirs(output_dir, exist_ok=True)

── Save clipped raster ──
pipeline.py:154  clipped_path = f"{output_dir}/clipped.tif"
pipeline.py:155  save_raster(clipped_path, clipped, raster.meta, transform, raster.crs)
                      #                                  ↓
                      # output/saver.py:8  def save_raster(output_path, data, metadata, transform, crs):
                      # output/saver.py:9-20    out_meta = metadata.copy()
                      #                         # For NDVI (2D): count=1, dtype=float32
                      #                         # For clipped (3D): keeps original metadata
                      #                         with rasterio.open(path, "w", **out_meta) as dst:
                      #                             dst.write(data)
Output: data/api_outputs/a1b2c3d4/clipped.tif

── Save NDVI raster ──
pipeline.py:159  ndvi_path = f"{output_dir}/ndvi.tif"
pipeline.py:160  save_raster(ndvi_path, ndvi, raster.meta, transform, raster.crs)
                      #                                  ↓
                      # output/saver.py:8-20  (same as above, but ndvi is 2D → count=1, dtype=float32)
Output: data/api_outputs/a1b2c3d4/ndvi.tif

── Save NDVI preview PNG ──
pipeline.py:164  ndvi_png_path = f"{output_dir}/ndvi.png"
pipeline.py:165  save_ndvi_preview(ndvi, ndvi_png_path)
                      #                                  ↓
                      # output/saver.py:23  def save_ndvi_preview(ndvi, output_path):
                      # output/saver.py:24      fig, ax = plt.subplots(figsize=(8, 6))
                      # output/saver.py:25      im = ax.imshow(ndvi, cmap="RdYlGn", vmin=-1, vmax=1)
                      # output/saver.py:26      plt.colorbar(im, ax=ax, label="NDVI")
                      # output/saver.py:27      ax.set_title("NDVI")
                      # output/saver.py:28      ax.axis("off")
                      # output/saver.py:29      plt.savefig(output_path, bbox_inches="tight")
                      # output/saver.py:30      plt.close()
                      #                                  ↓
                      # Matplotlib renders RdYlGn colormap:
                      #   Red   → Poor vegetation (NDVI < 0.2)
                      #   Yellow→ Moderate (0.2-0.5)
                      #   Green → Healthy (> 0.5)
Output: data/api_outputs/a1b2c3d4/ndvi.png

── Save processing report ──
pipeline.py:169  self.results["output_dir"] = output_dir
pipeline.py:170  self.results["ndvi_path"] = ndvi_path
pipeline.py:171  clipped_shape = clipped.shape
pipeline.py:172  self.results["clipped_size"] = {"bands": ..., "height": ..., "width": ...}
pipeline.py:177  self.results["status"] = "success"
pipeline.py:178  report_path = f"{output_dir}/processing_report.json"
pipeline.py:179  save_json_report(self.results, report_path)
                      #                                  ↓
                      # output/saver.py:33  def save_json_report(report, output_path):
                      # output/saver.py:34      with open(output_path, "w") as f:
                      # output/saver.py:35          json.dump(report, f, indent=4)
Output: data/api_outputs/a1b2c3d4/processing_report.json

── Cleanup ──
pipeline.py:182  raster.close()
                      #         ← closes the rasterio DatasetReader (releases file handle)

pipeline.py:183  logger.info("Pipeline completed successfully")
pipeline.py:184  return self.results
```

**Possible failures here:**
- `PermissionError`: Cannot write to output directory
- `rasterio.errors.RasterioIOError`: Cannot create GeoTIFF (disk full, invalid metadata)

---

## Entry Point 3: Standalone Phase Scripts

These scripts bypass the pipeline and run a single phase directly. Use them to isolate and debug specific steps.

### `python app/main_ndvi.py`

```
Flow:  multispectral.tif → load → extract_metadata → load_boundary →
       reproject → clip → calculate_ndvi → save_tif → save_png → stats → health_report

Outputs:
  data/ndvi/ndvi.tif
  data/ndvi/ndvi.png
  data/ndvi/ndvi_stats.json
  data/ndvi/health_report.json
```

### `python app/main_dos.py`

```
Flow:  multispectral.tif → load → ndvi_before → DOS correction →
       ndvi_after → comparison → report

Outputs:
  data/dos/red_corrected.tif
  data/dos/nir_corrected.tif
  data/dos/ndvi_before.png
  data/dos/ndvi_after.png
  data/dos/ndvi_comparison.png
  data/dos/dos_report.json
```

### `python app/main_mosaic.py`

```
Flow:  data/tiles/tile_*.tif → validate → merge → preview → report

Outputs:
  data/mosaic/merged.tif
  data/mosaic/merged_preview.png
  data/mosaic/mosaic_report.json
```

### `python app/main_preprocess.py`

```
Flow:  multispectral.tif → load → validate → scl_cloud_detect →
       cloud_mask → dos_correct → export_corrected → quality_report → ndvi

Outputs:
  data/preprocessing/cloud_mask.tif
  data/preprocessing/corrected/corrected_red.tif
  data/preprocessing/corrected/corrected_nir.tif
  data/preprocessing/quality_report.json
  data/preprocessing/ndvi/ndvi.tif
  data/preprocessing/ndvi/ndvi.png
```

---

## Data Shape Flow

Visual trace of how the data changes dimensions at each step:

```
rasterio.open(path)
  ↓
DatasetReader
  .read()
  ↓
numpy.ndarray (5, 100, 100)     ← (bands, height, width)  uint16

rasterio.mask.mask(raster, geometry, crop=True)
  ↓
numpy.ndarray (5, 57, 40)       ← (bands, height, width)  uint16  (clipped)

cloud_mask detection
  ↓
cloud_mask:     numpy.ndarray (57, 40)      bool
apply_cloud_mask → NaN on bands 0-3
  ↓
masked:         numpy.ndarray (5, 57, 40)   float32   (clouds = NaN)

dark_object_subtraction(red)   →  red_corrected:    (57, 40)  float32
dark_object_subtraction(nir)   →  nir_corrected:    (57, 40)  float32

calculate_ndvi(red, nir)
  ↓
ndvi:           numpy.ndarray (57, 40)    float32   (-1.0 to +1.0)

ndvi[cloud_mask] = np.nan
  ↓
ndvi:           numpy.ndarray (57, 40)    float32   (clouds = NaN)

save_raster → ndvi.tif   (1 band, float32)
save_ndvi_preview → ndvi.png  (RGB, RdYlGn colormap)
```

---

## Error Propagation

```
Layer 1:  Function (e.g., load_raster, calculate_ndvi)
            │
            ▼  raises ValueError, rasterio.Error, np.AxisError, etc.
Layer 2:  Pipeline step (e.g., _load, _clip)
            │
            ▼  exception propagates unmodified
Layer 3:  PreprocessingPipeline.run()
            │
            ▼  exception propagates unmodified
Layer 4:  API route (preprocess function)
            │
            ▼  caught by except Exception as e
            │
            ▼  raises HTTPException(status_code=500, detail=str(e))
Layer 5:  FastAPI server
            │
            ▼  returns HTTP 500 to client
            │
Response:  {"detail": "No bands found in raster"}
```

If running via CLI (`python app/main_ndvi.py`), Layer 4 (API) is absent — the exception propagates to stdout with a full traceback.

---

## Debugging Quick Reference

| Symptom | Likely cause | Check |
|---|---|---|
| `FileNotFoundError` | Wrong path | Path is relative to CWD. Run from project root. |
| `CRSError` / "CRS missing" | GeoTIFF lacks CRS metadata | `rasterio.open(path).crs` in Python |
| `WindowError` | Boundary outside raster extent | Compare `boundary.total_bounds` vs `raster.bounds` |
| "No bands found" | Corrupt or invalid GeoTIFF | `rasterio.open(path).count` in Python |
| `FloatingPointError` in NDVI | Division by near-zero denominator | Add `+ 1e-10` to denominator (already in code) |
| Empty NDVI (all NaN) | Cloud mask covering everything | Check `cloud_percentage` in logs |
| NDVI mean = 0.00 | Red = NIR (no vegetation in scene) | Verify band indices (Red=3, NIR=4) |
| HTTP 500 with no detail | Unhandled exception in pipeline | Run `python app/main_ndvi.py` for full traceback |
| "No module named 'api'" | Wrong working directory | Run from project root, not from `app/` |
| API returns "Not Found" | Wrong URL prefix | All endpoints under `/api/v1/...` |
| Preview PNG is all one color | Normalization issue | Check `band.min()` and `band.max()` — constant array? |
