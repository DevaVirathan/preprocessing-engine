import logging

import numpy as np

from app.ingestion.raster_loader import load_raster
from app.ingestion.metadata import extract_metadata
from app.boundary.boundary_loader import load_boundary
from app.boundary.reproject import reproject_boundary
from app.preprocessing.subset import clip_raster
from app.correction.atmospheric import dark_object_subtraction
from app.analytics.ndvi import calculate_ndvi
from app.output.saver import save_raster, save_ndvi_preview, save_json_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class PreprocessingPipeline:

    def __init__(self, config=None):
        self.config = config or {}
        self.results = {
            "steps": [],
            "status": "pending",
        }

    # ---- internal step methods ----

    def _load(self, raster_path):
        logger.info("Loading raster: %s", raster_path)
        return load_raster(raster_path)

    def _load_boundary(self, boundary_path):
        logger.info("Loading boundary: %s", boundary_path)
        return load_boundary(boundary_path)

    def _validate(self, raster):
        from app.validation.validator import validate_raster
        logger.info("Validating raster...")
        validate_raster(raster)
        logger.info("Validation OK")

    def _reproject_boundary(self, boundary, target_crs):
        logger.info("Reprojecting boundary to %s...", target_crs)
        if str(boundary.crs) != str(target_crs):
            return reproject_boundary(boundary, target_crs)
        logger.info("CRS already matches")
        return boundary

    def _clip(self, raster, boundary):
        logger.info("Clipping raster to boundary...")
        geometry = [feature for feature in boundary.geometry]
        clipped, transform = clip_raster(raster, geometry)
        logger.info("Clipped shape: %s", clipped.shape)
        return clipped, transform

    def _cloud_mask(self, data, scl_band_idx=4):
        logger.info("Detecting and masking clouds...")
        if data.shape[0] <= scl_band_idx:
            logger.info("No SCL band available, skipping cloud mask")
            return data, None
        from app.cloud.detector import detect_clouds_from_scl
        from app.cloud.masker import apply_cloud_mask, compute_cloud_stats
        scl = data[scl_band_idx]
        mask = detect_clouds_from_scl(scl)
        stats = compute_cloud_stats(mask)
        logger.info("Cloud cover: %s%%", stats["cloud_percentage"])
        masked = data.astype(np.float32).copy()
        for i in range(data.shape[0]):
            if i != scl_band_idx:
                masked[i] = apply_cloud_mask(data[i], mask)
        return masked, mask

    def _dos_correct(self, red_band, nir_band):
        logger.info("Applying DOS atmospheric correction...")
        red_corrected, red_dark = dark_object_subtraction(red_band)
        nir_corrected, nir_dark = dark_object_subtraction(nir_band)
        logger.info("Red dark value: %s, NIR dark value: %s", red_dark, nir_dark)
        return red_corrected, nir_corrected, {
            "red_dark_pixel": round(float(red_dark), 2),
            "nir_dark_pixel": round(float(nir_dark), 2),
        }

    def _compute_ndvi(self, red, nir):
        logger.info("Computing NDVI...")
        red_filled = np.nan_to_num(red, nan=0)
        nir_filled = np.nan_to_num(nir, nan=0)
        ndvi = calculate_ndvi(red_filled, nir_filled)
        valid = ndvi[~np.isnan(ndvi)]
        if len(valid) > 0:
            logger.info("NDVI range: %.4f to %.4f, mean: %.4f",
                        valid.min(), valid.max(), valid.mean())
        return ndvi

    # ---- public run method ----

    def run(self, raster_path, boundary_path, output_dir="data/output",
            red_band=3, nir_band=4, scl_band=5):
        self.results = {
            "raster": raster_path,
            "boundary": boundary_path,
            "steps": [],
            "status": "running",
        }

        # Step 1: Load
        raster = self._load(raster_path)
        self.results["steps"].append("load")
        metadata = extract_metadata(raster)

        # Step 2: Validate
        self._validate(raster)
        self.results["steps"].append("validate")

        # Step 3: Load boundary
        boundary = self._load_boundary(boundary_path)
        self.results["steps"].append("load_boundary")

        # Step 4: Reproject boundary
        boundary = self._reproject_boundary(boundary, raster.crs)
        self.results["steps"].append("reproject")

        # Step 5: Clip
        clipped, transform = self._clip(raster, boundary)
        self.results["steps"].append("clip")

        # Step 6: Cloud mask
        masked, cloud_mask = self._cloud_mask(clipped, scl_band - 1)
        self.results["steps"].append("cloud_mask")

        # Step 7: DOS correction
        red_idx = red_band - 1
        nir_idx = nir_band - 1
        red_corrected, nir_corrected, dos_info = self._dos_correct(
            masked[red_idx], masked[nir_idx]
        )
        self.results["steps"].append("dos_correction")
        self.results["dos"] = dos_info

        # Step 8: NDVI
        ndvi = self._compute_ndvi(red_corrected, nir_corrected)
        if cloud_mask is not None:
            ndvi[cloud_mask] = np.nan
        self.results["steps"].append("ndvi")

        # Step 9: Save outputs
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Save clipped
        clipped_path = f"{output_dir}/clipped.tif"
        save_raster(clipped_path, clipped, raster.meta, transform, raster.crs)
        logger.info("Saved: %s", clipped_path)

        # Save NDVI GeoTIFF
        ndvi_path = f"{output_dir}/ndvi.tif"
        save_raster(ndvi_path, ndvi, raster.meta, transform, raster.crs)
        logger.info("Saved: %s", ndvi_path)

        # Save NDVI PNG
        ndvi_png_path = f"{output_dir}/ndvi.png"
        save_ndvi_preview(ndvi, ndvi_png_path)
        logger.info("Saved: %s", ndvi_png_path)

        # Save report
        self.results["output_dir"] = output_dir
        self.results["ndvi_path"] = ndvi_path
        clipped_shape = clipped.shape
        self.results["clipped_size"] = {
            "bands": clipped_shape[0],
            "height": clipped_shape[1],
            "width": clipped_shape[2],
        }
        self.results["status"] = "success"
        report_path = f"{output_dir}/processing_report.json"
        save_json_report(self.results, report_path)
        logger.info("Saved: %s", report_path)

        raster.close()
        logger.info("Pipeline completed successfully")
        return self.results
