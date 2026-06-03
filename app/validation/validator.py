import numpy as np


def validate_raster(raster):
    if raster.count == 0:
        raise ValueError("No bands found in raster")
    if raster.crs is None:
        raise ValueError("CRS is missing")
    if raster.width == 0 or raster.height == 0:
        raise ValueError("Raster has zero width or height")
    return True


def validate_band(band, name="band"):
    if band.size == 0:
        raise ValueError(f"Empty band: {name}")
    if band.ndim != 2:
        raise ValueError(f"Band {name} must be 2D, got shape {band.shape}")
    return True
