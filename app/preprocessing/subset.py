import json
from rasterio.mask import mask


def clip_raster(raster, geometry):
    clipped, transform = mask(raster, geometry, crop=True)
    return clipped, transform


def save_clipped_raster(clipped, transform, metadata, output_path, crs):
    out_meta = metadata.copy()
    out_meta.update({
        "height": clipped.shape[1],
        "width": clipped.shape[2],
        "transform": transform,
        "crs": crs,
    })
    from rasterio import open as rio_open
    with rio_open(output_path, "w", **out_meta) as dst:
        dst.write(clipped)


def build_processing_report(field_id, original, clipped_size, crs):
    return {
        "field_id": field_id,
        "original_width": original["width"],
        "original_height": original["height"],
        "original_bands": original["bands"],
        "clipped_width": clipped_size[1],
        "clipped_height": clipped_size[0],
        "crs": str(crs),
        "status": "success",
    }


def save_processing_report(report, output_path):
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
