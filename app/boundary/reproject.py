def reproject_boundary(boundary, target_crs):
    return boundary.to_crs(target_crs)
