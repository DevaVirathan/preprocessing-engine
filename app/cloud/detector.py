import numpy as np


# SCL class definitions (Sentinel-2 Scene Classification Layer)
SCL_CLOUD_CLASSES = [8, 9, 10]   # medium cloud, high cloud, thin cirrus
SCL_CLOUD_SHADOW = 3
SCL_SNOW_ICE = 11


def detect_clouds_from_scl(scl_band):
    """
    Detect cloud pixels using Sentinel-2 SCL band.
    Returns boolean mask: True = cloud.
    """
    return np.isin(scl_band, SCL_CLOUD_CLASSES)


def detect_clouds_threshold(blue_band, threshold=2000):
    """
    Fallback threshold-based cloud detection using blue band reflectance.
    Clouds scatter blue light strongly.
    """
    return blue_band > threshold


def detect_shadows_from_scl(scl_band):
    return scl_band == SCL_CLOUD_SHADOW
