import numpy as np


def handle_nodata(band, nodata_values=None):
    """
    Convert nodata values to NaN.
    """
    if nodata_values is None:
        nodata_values = [-9999, 0, 65535]
    band = band.astype(np.float32)
    for val in nodata_values:
        band[band == val] = np.nan
    return band


def rescale_band(band, in_min=0, in_max=10000, out_min=0, out_max=1):
    """
    Rescale band from input range to output range.
    Useful for visualization.
    """
    band = band.astype(np.float32)
    scale = (out_max - out_min) / (in_max - in_min)
    return (band - in_min) * scale + out_min
