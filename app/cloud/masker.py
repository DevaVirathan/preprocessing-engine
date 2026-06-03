import numpy as np


def apply_cloud_mask(band, cloud_mask):
    """
    Set cloud pixels to NaN.
    band: 2D numpy array
    cloud_mask: boolean array (True = cloud)
    """
    band = band.astype(np.float32)
    band[cloud_mask] = np.nan
    return band


def apply_cloud_mask_inplace(band, cloud_mask, nodata=0):
    """
    Set cloud pixels to nodata value (keeps dtype).
    """
    band[cloud_mask] = nodata
    return band


def compute_cloud_stats(cloud_mask):
    total = cloud_mask.size
    cloud_count = int(np.sum(cloud_mask))
    return {
        "cloud_pixels": cloud_count,
        "valid_pixels": total - cloud_count,
        "cloud_percentage": round(cloud_count / total * 100, 2),
    }
