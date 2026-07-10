import os
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio import features, windows
from sklearn.neighbors import BallTree
from shapely.geometry.base import BaseGeometry
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from __setting import stdCityName
from analysis import analysisByCities
from .accessibilityRaster import _removeEmptyDirs

def accessibilityRaster_Country(
    data: analysisByCities,
    evcs: str, pop: str,
    savePath: str,
    thres: int = 10,
    blockSize: int = 4096, maxThread: int = 1
) -> None:
    dataDf = data.cdf
    savePath = os.path.join(savePath, "accessibility")
    bar = data.bar("Calculating accessibility", countryLevel=True)

    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["level1", "geometry"]]

    # Projection
    if dataDf.crs is not None and dataDf.crs.to_epsg() != 4326:
        dataDf.to_crs(4326, inplace=True)
    elif dataDf.crs is None:
        raise RuntimeError("Input analysis data do not have CRS.")
    if evcsDf.crs is not None and evcsDf.crs.to_epsg() != 4326:
        evcsDf.to_crs(4326, inplace=True)
    elif evcsDf.crs is None:
        raise RuntimeError("EVCS data do not have CRS.")

    # Process by country group
    for row in dataDf[["iso3_code", "geometry"]].itertuples():
        iso3 = getattr(row, "iso3_code")
        geom: BaseGeometry = getattr(row, "geometry")
        bar.set_postfix(iso3=iso3)

        popPath = os.path.join(
            pop,
            "population_All",
            "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
        )

        if os.path.exists(popPath):
            subEVCSDf = evcsDf.loc[evcsDf["level1"] == iso3]
            bar.set_description(f"Calculating spatial coverage of EVCS for {iso3}")
            __processByCountry(iso3, geom, subEVCSDf, popPath, thres, blockSize, maxThread, os.path.join(savePath, str(iso3)))
            bar.update()
        
        else:
            bar.update()
    
    bar.close()
    _removeEmptyDirs(savePath)

    return

def __processByCountry(
    iso3: str, geom: BaseGeometry,
    evcsDf: gpd.GeoDataFrame, popPath: str,
    thres: int, blockSize: int, maxThread: int,
    savePath: str,
) -> None:
    if not os.path.exists(savePath): os.makedirs(savePath)
    tifPath = os.path.join(
        savePath,
        "{}.tif".format(stdCityName(iso3))
    )
    emptyPath = os.path.join(
        savePath,
        "{}.txt".format(stdCityName(iso3))
    )

    # Skip processed
    if os.path.exists(tifPath) or os.path.exists(emptyPath):
        return
    
    # Skip empty EVCS
    if evcsDf.empty:
        return
    elif evcsDf.shape[0] <= thres:
        with open(emptyPath, 'w') as _:
            return
    
    # Get raster meta data
    with rio.open(popPath) as src:
        crs = src.crs
        if crs.to_epsg() != 4326:
            raise RuntimeError("Input population data is not WGS84")
        rows, cols = src.height, src.width
        transform = src.transform
        nodata = src.nodata
    
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

    hasData = False
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

    if iso3 in {"RUS", "USA"}:
        meta["BIGTIFF"] = "YES"

    with rio.open(
        tifPath, 'w',
        options=["NUM_THREADS=ALL_CPUS"],
        **meta
    ) as dst:
        futures = []
        writeLock = Lock()
        with ThreadPoolExecutor(max_workers=maxThread) as executor:
            for rowOff in range(0, windowH, blockSize):
                h = min(blockSize, windowH - rowOff)
                for colOff in range(0, windowW, blockSize):
                    w = min(blockSize, windowW - colOff)
                    blockWindow = windows.Window(
                        colStart + colOff, # type: ignore
                        rowStart + rowOff,
                        w, h
                    )
                    # 块的 transform（用于 geom_mask）
                    blockTrans = windows.transform(blockWindow, transform)
                    future = executor.submit(
                        __processBlock,
                        popPath, nodata,
                        blockWindow, blockTrans,
                        rowOff, colOff,
                        geom,
                        transform,
                        tree
                    )
                    futures.append(future)

            for future in as_completed(futures):
                try:
                    futureResult = future.result()
                except Exception as e:
                    for f in futures:
                        f.cancel()
                    raise RuntimeError(f"Error processing block: {e}")
                
                if futureResult is not None:
                    blockDist, rowOff, colOff = futureResult
                    h, w = blockDist.shape
                    with writeLock:
                        dst.write(blockDist, 1, window=windows.Window(colOff, rowOff, w, h)) # type: ignore
                        hasData = True

    if not hasData:
        os.remove(tifPath)

    return

def __processBlock(
    popPath: str, nodata: Any,
    blockWindowdow: windows.Window,
    blockTransform: rio.Affine,
    rowOff: int, colOff: int,
    geom: BaseGeometry,
    transform: rio.Affine,
    tree: BallTree
) -> tuple[np.ndarray, int, int] | None:
    with rio.open(popPath) as blockSrc:
        popArray = blockSrc.read(1, window=blockWindowdow)

    # 有效像元掩膜
    valid = ~np.isnan(popArray)
    if nodata is not None:
        valid &= (popArray != nodata)

    # 几何体掩膜
    geom_mask = features.geometry_mask(
        [geom],
        out_shape=popArray.shape,
        transform=blockTransform,
        invert=True
    )
    valid &= geom_mask

    if not np.any(valid):
        return None

    # Get index
    rowsIdx, colsIdx = np.where(valid)
    globalRows = rowsIdx + rowOff
    globalCols = colsIdx + colOff
    xs, ys = transform * (globalCols, globalRows) # type: ignore
    popCoords = np.radians(np.column_stack([ys, xs]))

    # 查询最近充电站距离（弧度）
    distances, _ = tree.query(popCoords, k=1)
    distances = distances.flatten() * 6371000.0

    # 生成块的结果数组
    blockDist = np.full(popArray.shape, np.nan, dtype=np.float32)
    blockDist[rowsIdx, colsIdx] = distances.astype(np.float32)

    return blockDist, rowOff, colOff