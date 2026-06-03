import geopandas as gpd


def load_boundary(path):
    return gpd.read_file(path)
