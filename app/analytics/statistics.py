import numpy as np


def calculate_ndvi_stats(ndvi):
    return {
        "min": round(float(ndvi.min()), 4),
        "max": round(float(ndvi.max()), 4),
        "mean": round(float(ndvi.mean()), 4),
        "median": round(float(np.median(ndvi)), 4),
        "std": round(float(ndvi.std()), 4),
    }
