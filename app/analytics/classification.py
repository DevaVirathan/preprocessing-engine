import numpy as np


def classify_ndvi(value):
    if value < 0.2:
        return "Poor"
    elif value < 0.5:
        return "Moderate"
    return "Healthy"


def health_summary(ndvi):
    total = ndvi.size
    healthy = int(np.sum(ndvi >= 0.5))
    moderate = int(np.sum((ndvi >= 0.2) & (ndvi < 0.5)))
    poor = int(np.sum(ndvi < 0.2))
    return {
        "healthy_pct": round(healthy / total * 100, 1),
        "moderate_pct": round(moderate / total * 100, 1),
        "poor_pct": round(poor / total * 100, 1),
    }


def build_health_report(field_id, ndvi_stats, health_summary):
    mean_ndvi = ndvi_stats["mean"]
    if mean_ndvi >= 0.5:
        status = "Healthy"
    elif mean_ndvi >= 0.2:
        status = "Moderate"
    else:
        status = "Poor"
    return {
        "field_id": field_id,
        "mean_ndvi": mean_ndvi,
        "max_ndvi": ndvi_stats["max"],
        "min_ndvi": ndvi_stats["min"],
        "health_status": status,
        "healthy_pct": health_summary["healthy_pct"],
        "moderate_pct": health_summary["moderate_pct"],
        "poor_pct": health_summary["poor_pct"],
    }
