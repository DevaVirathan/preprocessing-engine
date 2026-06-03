import rasterio


def validate_tiles(tile_paths):
    if not tile_paths:
        raise ValueError("No tile paths provided")

    crs_list = []
    count_list = []
    resolutions = []

    for path in tile_paths:
        with rasterio.open(path) as src:
            crs_list.append(src.crs)
            count_list.append(src.count)
            resolutions.append(src.res)

    crs_ok = len(set(str(c) for c in crs_list)) == 1
    bands_ok = len(set(count_list)) == 1
    res_ok = len(set(resolutions)) == 1

    return {
        "valid": crs_ok and bands_ok and res_ok,
        "same_crs": crs_ok,
        "same_bands": bands_ok,
        "same_resolution": res_ok,
        "tile_count": len(tile_paths),
        "crs": str(crs_list[0]) if crs_ok else "MISMATCH",
        "bands": count_list[0] if bands_ok else "MISMATCH",
        "resolution": str(resolutions[0]) if res_ok else "MISMATCH",
    }
