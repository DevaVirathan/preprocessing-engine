import numpy as np


def dark_object_subtraction(band, percentile=1):
    """
    Dark Object Subtraction (DOS) atmospheric correction.
    Assumes darkest pixels in the scene should be near-zero reflectance.
    Subtracts the percentile value from all pixels.
    """
    band = band.astype(np.float32)
    dark_value = np.percentile(band[band > 0], percentile)
    corrected = band - dark_value
    corrected[corrected < 0] = 0
    return corrected, dark_value


def dos_correct_raster(raster_data, band_indices, percentile=1):
    """
    Apply DOS to multiple bands.
    raster_data: 3D array (bands, height, width)
    band_indices: list of band indices to correct
    Returns corrected array and list of dark values.
    """
    dark_values = {}
    corrected = raster_data.copy().astype(np.float32)
    for idx in band_indices:
        corrected[idx], dv = dark_object_subtraction(raster_data[idx], percentile)
        dark_values[f"band_{idx + 1}"] = round(float(dv), 2)
    return corrected, dark_values
