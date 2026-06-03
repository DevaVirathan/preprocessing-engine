import numpy as np


def validate_band(band, name="band"):
    if band.size == 0:
        raise ValueError(f"Empty band: {name}")
    if band.ndim != 2:
        raise ValueError(f"Band {name} must be 2D, got shape {band.shape}")
    return True


def validate_raster(raster_data, expected_bands=None):
    if raster_data.ndim != 3:
        raise ValueError(f"Raster must be 3D (bands, h, w), got shape {raster_data.shape}")
    if expected_bands and raster_data.shape[0] != expected_bands:
        raise ValueError(f"Expected {expected_bands} bands, got {raster_data.shape[0]}")
    for i in range(raster_data.shape[0]):
        validate_band(raster_data[i], f"band_{i+1}")
    return True


def quality_report(cloud_stats, dark_values, corrections_applied):
    return {
        "cloud_pixels": cloud_stats["cloud_pixels"],
        "valid_pixels": cloud_stats["valid_pixels"],
        "cloud_percentage": cloud_stats["cloud_percentage"],
        "atmospheric_correction": "DOS",
        "dark_values": dark_values,
        "corrections_applied": corrections_applied,
        "status": "success",
    }
