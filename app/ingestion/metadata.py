def extract_metadata(raster):
    return {
        "width": raster.width,
        "height": raster.height,
        "bands": raster.count,
        "crs": str(raster.crs),
        "resolution": raster.res,
        "bounds": str(raster.bounds),
    }


def validate_raster(raster):
    if raster.count == 0:
        raise Exception("No bands found")
    if raster.crs is None:
        raise Exception("CRS missing")
    return True
