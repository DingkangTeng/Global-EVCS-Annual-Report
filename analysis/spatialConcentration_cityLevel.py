import os
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio import windows, features
from shapely.geometry.base import BaseGeometry
from shapely.geometry import box

from .byCities import analysisByCities

def spatialConcentration(data: analysisByCities, evcsThres: int = 10):
    df = data.df
    dfCrs = data.crs
    bar = data.bar("Calculating spatial concentration of EVCS", 1)
    col = "spatialConcentration"
    df[col] = np.nan

    with (
        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
        rio.open(os.path.join(data.savePath, "evcs.tif"), options=["NUM_THREADS=ALL_CPUS"]) as src
    ):
        if dfCrs != src.crs.to_epsg(): df = df.to_crs(src.crs)

        # Filter outside data
        rasterPoly = box(*src.bounds)
        dfFiltered = df[df.geometry.intersects(rasterPoly)]

        for row in dfFiltered[["disp_en", "geometry"]].itertuples():
            idx = getattr(row, "Index")
            city = getattr(row, "disp_en")
            geom: BaseGeometry = getattr(row, "geometry")
            
            bar.set_description(f"Calculating spatial coverage of EVCS for {city:<25.25}") # <max.min

            # Cut raster
            minx, miny, maxx, maxy = geom.bounds
            window = windows.from_bounds(minx, miny, maxx, maxy, src.transform)
            if window.width == 0 or window.height == 0:
                bar.update()
                continue
            raster = src.read(1, window=window, boundless=True, fill_value=src.nodata)
            transform = src.window_transform(window)
            shape = raster.shape
            if shape[0] == 0 or shape[1] == 0:
                bar.update()
                continue

            cityMask = features.geometry_mask(
                [geom],
                out_shape=shape,
                transform=transform,
                invert=True,
                all_touched=False
            )

            validMask = (raster != src.nodata) & ~np.isnan(raster) & cityMask
            cityVals = raster[validMask]
            evcsNum = np.sum(cityVals)

            if evcsNum == 0:
                bar.update()
                continue
            elif evcsNum <= evcsThres:
                data.df.at[idx, col] = -100
                bar.update()
                continue
            
            data.df.at[idx, col] = __calIndex(cityVals)

            bar.update()

    bar.set_description("Saving results for \"spatialConcentration\"")
    data.updateData(
        (col, "REAL", None, False)
    )
    bar.n = bar.total
    bar.refresh()
    bar.close()

    return

def __calIndex(raster: np.ndarray, mainData: bool = True) -> float:
    if mainData or (not mainData and len(raster) > 1):
        raster = np.sort(raster)
        top = raster[-int(np.ceil(len(raster) * 0.1)):]
    
        return np.sum(top) / np.sum(raster)
    
    elif not mainData and len(raster) == 1:
        return 1
    
    else:
        return -100