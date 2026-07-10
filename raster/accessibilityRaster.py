import os
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio import features, windows
from sklearn.neighbors import BallTree
from shapely.geometry.base import BaseGeometry
from tqdm import tqdm
from typing import Any

from __setting import stdCityName
from analysis import analysisByCities

def accessibilityRaster(data: analysisByCities, evcs: str, pop: str, savePath: str, thres: int = 10) -> None:
    dataDf = data.df
    savePath = os.path.join(savePath, "accessibility")
    bar = data.bar("Calculating accessibility")

    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["level1", "geometry"]]

    # Process by country group
    for iso3, countryDf in dataDf[["iso3_code", "disp_en", "geometry"]].groupby("iso3_code"):
        countryDf = gpd.GeoDataFrame(countryDf, crs=dataDf.crs)
        bar.set_postfix(iso3=iso3)

        popPath = os.path.join(
            pop,
            "population_All",
            "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
        )

        if os.path.exists(popPath):
            subEVCSDf = evcsDf.loc[evcsDf["level1"] == iso3]
            with (
                rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
                rio.open(popPath) as src
            ):
                __processByCountry(countryDf, subEVCSDf, src, thres, os.path.join(savePath, str(iso3)), bar)
                
        
        else:
            bar.update(countryDf.shape[0])
    
    bar.close()
    _removeEmptyDirs(savePath)

    return

def __processByCountry(
    countryDf: gpd.GeoDataFrame,
    evcsDf: gpd.GeoDataFrame, src: Any,
    thres: int, savePath: str,
    bar: tqdm
) -> None:
    if not os.path.exists(savePath): os.makedirs(savePath)
    # Unify projection
    crs = src.crs
    if crs.to_epsg() != 4326:
        raise RuntimeError("Input population data is not WGS84")
    if evcsDf.crs is not None and evcsDf.crs.to_epsg() != 4326:
        evcsDf.to_crs(4326, inplace=True)
    elif evcsDf.crs is None:
        raise RuntimeError("EVCS data do not have CRS.")
    
    rows, cols = src.height, src.width
    transform = src.transform
    nodata = src.nodata
    
    for row in countryDf[["disp_en", "geometry"]].itertuples():
        city = getattr(row, "disp_en")
        geom: BaseGeometry = getattr(row, "geometry")
        tifPath = os.path.join(
            savePath,
            "{}.tif".format(stdCityName(city))
        )
        emptyPath = os.path.join(
            savePath,
            "{}.txt".format(stdCityName(city))
        )

        # Skip processed
        if os.path.exists(tifPath):
            bar.update()
            continue

        bar.set_description(f"Calculating spatial coverage of EVCS for {city:<25.25}") # <max.min

        # Filter EVCS by city boundary
        possibleMatchesIdx = evcsDf.sindex.intersection(geom.bounds)
        # No EVCS
        if possibleMatchesIdx.shape[0] == 0:
            bar.update()
            continue
        candidates = evcsDf.iloc[possibleMatchesIdx]
        subEVCS: gpd.GeoDataFrame = candidates[candidates.within(geom)]
        if subEVCS.empty:
            bar.update()
            continue
        elif subEVCS.shape[0] <= thres:
            with open(emptyPath, 'w') as _:
                bar.update()
            continue
        
        # Build trees for EVCS
        evcsCoords = np.array([(p.x, p.y) for p in evcsDf.geometry]) # type: ignore
        evcsCoords = np.radians(evcsCoords[:, ::-1])
        tree = BallTree(evcsCoords, metric="haversine")
        
        # Get city population raster
        window = windows.from_bounds(*geom.bounds, transform).round_offsets().round_lengths()
        ## Get rows and cols for window based on geometry
        rowStart = max(0, int(window.row_off))
        rowStop = min(rows, rowStart + int(window.height))
        colStart = max(0, int(window.col_off))
        colStop = min(cols, colStart + int(window.width))
        window = windows.Window(colStart, rowStart, colStop - colStart, rowStop - rowStart) # type: ignore
        windowH = rowStop - rowStart
        windowW = colStop - colStart
        windowTransform = src.window_transform(window)

        # Read population data
        popArray = src.read(1, window=window)
        geomMask = features.geometry_mask(
            [geom],
            out_shape=(windowH, windowW),
            transform=windowTransform,
            invert=True
        )

        validMask: np.ndarray = ~np.isnan(popArray)
        if nodata is not None:
            validMask &= (popArray != nodata)
        validMask &= geomMask

        if not np.any(validMask):
            # No population
            bar.update()
            continue
        
        # Get the valid coordination in the window
        ## Rows and cols index for all pixel in the window
        rowsIdx, colsIdx = np.where(validMask)
        ## Transform the rows and cols in the window to the global number
        globalRows = rowsIdx + rowStart
        globalCols = colsIdx + colStart
        xs, ys = transform * (globalCols, globalRows)

        ## Creat central coordinate for population
        popCoords = np.stack([xs, ys], axis=1)
        popCoords = np.radians(popCoords[:, ::-1])

        distances, _ = tree.query(popCoords, k=1)

        # Save
        ## Skip no data country
        if np.sum(distances) == 0:
            bar.update()
            continue

        distances = distances.flatten() * 6371000.0
        result = np.full((windowH, windowW), np.nan, dtype=np.float32)
        result[rowsIdx, colsIdx] = distances.astype(np.float32)

        meta = {
            "driver": "GTiff",
            "height": windowH,
            "width": windowW,
            "count": 1,
            "dtype": np.float32,
            "crs": crs,
            "transform": windowTransform,
            "compress": "lzw",
            "nodata": np.nan
        }

        with rio.open(
            tifPath, 'w',
            options=["NUM_THREADS=ALL_CPUS"],
            **meta
        ) as dst:
            dst.write(result, 1)

        bar.update()

    return

def _removeEmptyDirs(path: str) -> None:
    """
    Delete empty folder
    """
    if not os.path.isdir(path):
        return
    # Using topdown=False to process subdirectory
    for root, dirs, _ in os.walk(path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Whether empty folder
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            # Ignore folder cannot access
            except OSError:
                pass