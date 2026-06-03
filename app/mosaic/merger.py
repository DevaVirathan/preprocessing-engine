import rasterio
from rasterio.merge import merge


def create_mosaic(tile_paths, output_path):
    datasets = [rasterio.open(path) for path in tile_paths]
    mosaic, transform = merge(datasets)

    metadata = datasets[0].meta.copy()
    metadata.update({
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": transform,
    })

    with rasterio.open(output_path, "w", **metadata) as dst:
        dst.write(mosaic)

    for ds in datasets:
        ds.close()

    return output_path
