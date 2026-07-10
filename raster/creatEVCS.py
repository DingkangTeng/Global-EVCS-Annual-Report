import os
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.transform import from_origin

from __setting import EPSG

def creatEVCS(evcs: str, savePath: str, gridSize: int = 1000, geographic: str = "AREA") -> None:
    crs, xLim, yLim = EPSG(geographic)
    gdf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["geometry"]]
    gdf = gdf.to_crs(crs) if (gdf.crs is not None and gdf.crs.to_epsg() != crs) or gdf.crs is None else gdf

    xCoords = gdf.geometry.x.to_numpy()
    yCoords = gdf.geometry.y.to_numpy()

    # Initialize boundary
    xmin, ymin, xmax, ymax = gdf.total_bounds
    buffer = 200
    xmin = -xLim if (xmin - buffer) < -xLim else xmin - buffer
    xmax = xLim if (xmax + buffer) > xLim else xmax + buffer
    ymin = yLim if (ymin - buffer) < -yLim else ymin - buffer
    ymax = yLim if (ymax + buffer) > yLim else ymax + buffer

    width = int(np.ceil((xmax - xmin) / gridSize))
    height = int(np.ceil((ymax - ymin) / gridSize))

    # Creat raster
    xEdges = np.linspace(xmin, xmax, width + 1)
    yEdges = np.linspace(ymin, ymax, height + 1)
    counts, _, _ = np.histogram2d(yCoords, xCoords, bins=(yEdges, xEdges))
    ## Flip up and down to conform to the storage order of GeoTIFF from top to bottom
    counts = np.flipud(counts)
    ## Specify data type to save storge space
    counts = counts.astype(np.uint16) if counts.max() < 65535 else counts.astype(np.uint32)
    ## Raster meta data
    transform = from_origin(xmin, ymax, gridSize, gridSize)
    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": counts.dtype,
        "crs": crs,
        "transform": transform,
        "compress": "lzw",
        "nodata": 0
    }

    with rio.open(
        os.path.join(savePath, "evcs.tif"), 'w',
        options=["NUM_THREADS=ALL_CPUS"],
        **meta
    ) as dst:
        dst.write(counts, 1)

    return