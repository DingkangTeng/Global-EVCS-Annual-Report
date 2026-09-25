import os, gc
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window, transform
from concurrent.futures import ThreadPoolExecutor, as_completed
from shapely.geometry.base import BaseGeometry
from tqdm import tqdm
from typing import Any

from __setting import getUtmZone, projectGeom, checkCRS
from .byCities import analysisByCities

def spatialCoverage_Country(
    data: analysisByCities,
    evcs: str, poi: str, pop: str,
    buffer: int = 1000,
    thres: int = 10, maxThread: int = 1, block: int = 2048
) -> None:
    dataDf = data.cdf
    bar = data.bar("Calculating spatial coverage of EVCS", 1, countryLevel=True)
    tqdm.write("Reading POI data may take several minutes.")
    # All
    col = "spatialCoverage"
    dataDf[col] = np.nan
    col2 = "spatialCoverageForPOI1"
    dataDf[col2] = np.nan
    col3 = "spatialCoverageForPOI2"
    dataDf[col3] = np.nan
    col4 = "spatialCoverageForPOI3"
    dataDf[col4] = np.nan
    col5 = "spatialCoverageForPop"
    dataDf[col5] = np.nan
    
    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["level1", "geometry"]]
    checkCRS(evcsDf, dataDf)
    groupedEVCS = {
        iso: gpd.GeoDataFrame(
            group, geometry="geometry", crs=evcsDf.crs
        ) for iso, group in evcsDf.groupby("level1")
    }
    
    poiDf = gpd.read_parquet(poi, filters=[("fsq_category_ids", "in", [1, 2, 3])])
    checkCRS(poiDf, dataDf)
    groupedPOI = {
        iso: gpd.GeoDataFrame(
            group, geometry="geometry", crs=poiDf.crs
        ) for iso, group in poiDf.groupby("level1")
    }
    del poiDf, evcsDf
    gc.collect()

    # Process by country group
    futures = []
    with ThreadPoolExecutor(max_workers=maxThread) as executor:
        for row in dataDf.itertuples():
            idx = getattr(row, "Index")
            iso3 = getattr(row, "iso3_code")
            geometry: BaseGeometry = getattr(row, "geometry")

            subEVCSDf = groupedEVCS.get(iso3, gpd.GeoDataFrame())
            if subEVCSDf.empty:
                bar.update()
                continue

            subPOIDf = groupedPOI.get(iso3, gpd.GeoDataFrame())
            popPath = os.path.join(
                pop,
                "population_All",
                "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            )

            popPath = popPath if os.path.exists(popPath) else None
            futures.append(
                executor.submit(
                    _processByCountry, dataDf, geometry, idx, subEVCSDf, subPOIDf, popPath, buffer, thres, iso3, bar, block
                )
            )

        for future in as_completed(futures):
            try:
                iso3 = future.result()
                del groupedEVCS[iso3]
                del groupedPOI[iso3]
                bar.set_description("{} finished".format(iso3))
            except Exception as e:
                raise RuntimeError(e)

    bar.set_description("Saving results for \"spatial coverage\"")
    data.updateData(
        (col, "REAL", None, False),
        (col2, "REAL", None, False),
        (col3, "REAL", None, False),
        (col4, "REAL", None, False),
        (col5, "REAL", None, False),
        countryLevel=True
    )
    bar.update()
    bar.close()
    
    return

def _processByCountry(
    dataDf: gpd.GeoDataFrame, geom: BaseGeometry, idx: Any,
    evcsDf: gpd.GeoDataFrame, poiDf: gpd.GeoDataFrame,
    popPath: str | None,
    buffer: int, thres: int,
    iso3: str, bar: tqdm,
    block: int
) -> Any:
    # Get all EVCS
    possibleMatchesIdx = evcsDf.sindex.intersection(geom.bounds)

    # No EVCS
    if possibleMatchesIdx.shape[0] == 0:
        bar.update()
        return iso3
    candidates = evcsDf.iloc[possibleMatchesIdx]
    subEVCS: gpd.GeoDataFrame = candidates[candidates.within(geom)]
    if subEVCS.empty:
        bar.update()
        return iso3
    elif subEVCS.shape[0] <= thres:
        dataDf.at[idx, "spatialCoverage"] = -100
        dataDf.at[idx, "spatialCoverageForPOI1"] = -100
        dataDf.at[idx, "spatialCoverageForPOI2"] = -100
        dataDf.at[idx, "spatialCoverageForPOI3"] = -100
        dataDf.at[idx, "spatialCoverageForPop"] = -100
        bar.update()
        return iso3
    
    # Calculate Spatial Coverage of Charging Stations
    ## Project to UTM
    utm = getUtmZone(geom.centroid.y, geom.centroid.x)
    geomUTM = projectGeom(geom, dataDf.crs, utm)
    evcsBuffer = subEVCS.geometry.to_crs(utm).buffer(buffer).union_all().intersection(geomUTM)
    evcsArea = evcsBuffer.area
    geomArea = geomUTM.area
    
    sCover = evcsArea / geomArea
    dataDf.at[idx, "spatialCoverage"] = sCover

    # Change buffer back to wgs84
    evcsBuffer = projectGeom(evcsBuffer, utm, 4326)
    del geomUTM

    #Population
    if popPath is not None:
        result = _calculatePop(popPath, geom, evcsBuffer, block)
        if result is not None:
            dataDf.at[idx, "spatialCoverageForPop"] = result
    bar.update(0.5)

    # POI
    ## Check poi data
    if poiDf.empty:
        bar.update(0.5)
        return iso3
    
    ## Calculate
    result = _calculatePOI(poiDf, geom, evcsBuffer)
    if result is not None:
        dataDf.at[idx, "spatialCoverageForPOI1"] = result[0]
        dataDf.at[idx, "spatialCoverageForPOI2"] = result[1]
        dataDf.at[idx, "spatialCoverageForPOI3"] = result[2]
    bar.update(0.5)

    return iso3

def _calculatePop(
    popPath: str,
    geom: BaseGeometry, evcsBuffer: BaseGeometry,
    block: int
) -> float | None:
    # Population data is WGS84, no need for projection
    if geom.is_empty: return
    
    with (
        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
        rio.open(popPath) as src
    ):
        # Check overlap
        rasterBounds = src.bounds  # (left, bottom, right, top)
        geomBounds = geom.bounds   # (minx, miny, maxx, maxy)
        if not (geomBounds[0] <= rasterBounds[2] and
                geomBounds[2] >= rasterBounds[0] and
                geomBounds[1] <= rasterBounds[3] and
                geomBounds[3] >= rasterBounds[1]):
            return
        
        # Process by chunk
        window = from_bounds(*geomBounds, transform=src.transform)
        ww = int(window.width)
        wh = int(window.height)
        if ww == 0 or wh == 0:
            return
        
        totalPop = 0.0
        EVCSCoveredPop = 0.0

        for rowOff in range(0, wh, block):
            height = min(block, wh - rowOff)
            for colOff in range(0, ww, block):
                width = min(block, ww - colOff)

                blockWin = Window(
                    window.col_off + colOff, # type: ignore
                    window.row_off + rowOff,
                    width, height
                )
                data = src.read(1, window=blockWin)

                # Get valid data
                valid = ~np.isnan(data) & (data != src.nodata)
                if not valid.any():
                    continue

                blockTransform = transform(blockWin, src.transform)
                cityMask = geometry_mask(
                    [geom], out_shape=data.shape,
                    transform=blockTransform, invert=True
                )
                bufferMask = geometry_mask(
                    [evcsBuffer], out_shape=data.shape,
                    transform=blockTransform, invert=True
                )

                totalPop += np.sum(data[cityMask & valid], dtype=np.float64)
                EVCSCoveredPop += np.sum(data[bufferMask & valid], dtype=np.float64)

        if totalPop == 0:
            return
        else:
            totalCover = EVCSCoveredPop / totalPop

    return totalCover

def _calculatePOI(
    poiDf: gpd.GeoDataFrame,
    geom: BaseGeometry, evcsBuffer: BaseGeometry
) -> np.ndarray | None:
    if geom.is_empty:
        return
    
    # Calculate Spatial Coverage of POI
    ## Get all POI
    possibleMatchesIdx = poiDf.sindex.intersection(geom.bounds)
    if possibleMatchesIdx.shape[0] == 0:
        return
    
    candidates = poiDf.iloc[possibleMatchesIdx]
    cityPOI = candidates[candidates.within(geom)]
    if cityPOI.empty:
        return
    
    # Intersection
    inEVCS = cityPOI.within(evcsBuffer)
    
    # By category
    result = np.full([3], np.nan, dtype=np.float64)
    for i in (1, 2, 3):
        cat = cityPOI["fsq_category_ids"] == i
        cityPOICategory = cityPOI[cat]

        totalPOI = cityPOICategory.shape[0]
        if totalPOI == 0: continue

        coverdPOI = inEVCS[cat].sum()
        result[i-1] = coverdPOI / totalPOI

    return result.flatten()
    # POI1, POI2, POI3