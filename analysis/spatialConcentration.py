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
    col2 = "spatialConcentration_BuiltUp" # 可以删
    df[col2] = np.nan
    col3 = "spatialConcentration_Other" # 可以删
    df[col3] = np.nan

    with (
        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
        rio.open(os.path.join(data.savePath, "evcs.tif"), options=["NUM_THREADS=ALL_CPUS"]) as src
    ):
        if dfCrs != src.crs.to_epsg(): df = df.to_crs(src.crs)

        # Filter outside data
        rasterPoly = box(*src.bounds)
        dfFiltered = df[df.geometry.intersects(rasterPoly)]
        # Load builtup and transform
        builtUpAll = gpd.read_file(data.builtup, layer="builtup").geometry
        builtUpAll = builtUpAll.to_crs(src.crs) if builtUpAll.crs is None or builtUpAll.crs.to_epsg() != src.crs.to_epsg() else builtUpAll

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
                data.df.at[idx, col2] = -100
                data.df.at[idx, col3] = -100
                bar.update()
                continue
            
            data.df.at[idx, col] = __calIndex(cityVals)

            # Calculate built up
            possibleMatch = builtUpAll.sindex.intersection(geom.bounds)
            if possibleMatch.size > 0:
                builtUp = gpd.GeoSeries(builtUpAll.iloc[possibleMatch])
                builtUp = builtUp[builtUp.intersects(geom)]
            else:
                builtUp = gpd.GeoSeries([])

            if len(builtUp) == 0:
                data.df.at[idx, col2] = -100
                data.df.at[idx, col3] = data.df.at[idx, col]
                bar.update()
                continue
            else:
                builtUp = builtUp.union_all() # type: ignore

            builtupMask = features.geometry_mask(
                [geom.intersection(builtUp)],
                out_shape=shape,
                transform=transform,
                invert=True,
                all_touched=False
            )

            data.df.at[idx, col2] = __calIndex(raster[validMask & builtupMask], mainData=False)
            data.df.at[idx, col3] = __calIndex(raster[validMask & ~builtupMask], mainData=False)

            bar.update()

    bar.set_description("Saving results for \"spatialConcentration\"")
    data.updateData(
        (col, "REAL", None, False),
        (col2, "REAL", None, False),
        (col3, "REAL", None, False)
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