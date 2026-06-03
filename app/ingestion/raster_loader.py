import rasterio


def load_raster(path: str):
    return rasterio.open(path)
