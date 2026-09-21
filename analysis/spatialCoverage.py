import os
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.mask import mask
from rasterio.features import geometry_mask
from concurrent.futures import ThreadPoolExecutor, as_completed
from shapely.geometry.base import BaseGeometry
from tqdm import tqdm

from __setting import getUtmZone, projectGeom, checkCRS
from .byCities import analysisByCities

def spatialCoverage(
    data: analysisByCities,
    evcs: str, poi: str, pop: str,
    buffer: int = 1000,
    thres: int = 10, maxThread: int = 1
) -> None:
    dataDf = data.df
    bar = data.bar("Calculating spatial coverage of EVCS", 1)
    tqdm.write("Reading POI and built-up area data may take several minutes.")
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
    col_3 = "spatialCoverage_Other"
    dataDf[col_3] = np.nan
    col2_3 = "spatialCoverageForPOI1_Other"
    dataDf[col2_3] = np.nan
    col3_3 = "spatialCoverageForPOI2_Other"
    dataDf[col3_3] = np.nan
    col4_3 = "spatialCoverageForPOI3_Other"
    dataDf[col4_3] = np.nan
    col5_3 = "spatialCoverageForPop_Other"
    dataDf[col5_3] = np.nan
    
    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["level1", "geometry"]]
    checkCRS(evcsDf, dataDf)
    poiDf = gpd.read_parquet(poi, filters=[("fsq_category_ids", "in", [1, 2, 3])])
    checkCRS(poiDf, dataDf)

    # Built up data CRS
    builtUpAll = gpd.read_file(data.builtup, layer="builtup").geometry
    builtUpAll = builtUpAll.to_crs(4326) if builtUpAll.crs is None or builtUpAll.crs.to_epsg() != 4326 else builtUpAll

    # Process by country group
    for iso3, countryDf in dataDf[["iso3_code", "disp_en", "geometry"]].groupby("iso3_code"):
        assert isinstance(countryDf, gpd.GeoDataFrame)
        bar.set_postfix(iso3=iso3)

        subEVCSDf = evcsDf.loc[evcsDf["level1"] == iso3]
        subPOIDf = poiDf.loc[poiDf["level1"] == iso3]
        popPath = os.path.join(
            pop,
            "population_All",
            "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
        )

        # Filter built-up area
        bbox = countryDf.geometry.total_bounds
        builtupInCountry = builtUpAll.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]

        popPath = popPath if os.path.exists(popPath) else None
        __processByCountry(dataDf, countryDf, subEVCSDf, subPOIDf, builtupInCountry, popPath, buffer, thres, bar, maxThread)

    bar.set_description("Saving results for \"spatialConcentration\"")
    data.updateData(
        (col, "REAL", None, False),
        (col2, "REAL", None, False),
        (col3, "REAL", None, False),
        (col4, "REAL", None, False),
        (col5, "REAL", None, False),
        (col_3, "REAL", None, False),
        (col2_3, "REAL", None, False),
        (col3_3, "REAL", None, False),
        (col4_3, "REAL", None, False),
        (col5_3, "REAL", None, False),
    )
    bar.update()
    bar.close()
    
    return

def __processByCountry(
    dataDf: gpd.GeoDataFrame, countryDf: gpd.GeoDataFrame,
    evcsDf: gpd.GeoDataFrame, poiDf: gpd.GeoDataFrame,
    builtUpAll: gpd.GeoSeries,
    popPath: str | None,
    buffer: int, thres: int,
    bar: tqdm, maxThread: int = 1
) -> None:
    futuresPOI = []
    futureDictPOI = {}
    futuresPop = []
    futureDictPop = {}
    with ThreadPoolExecutor(max_workers=maxThread) as executor:
        for row in countryDf[["disp_en", "geometry"]].itertuples():
            idx = getattr(row, "Index")
            city = getattr(row, "disp_en")
            geom: BaseGeometry = getattr(row, "geometry")
            
            bar.set_description(f"Calculating spatial coverage of EVCS for {city:<25.25}") # <max.min

            # Get all EVCS
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
                dataDf.at[idx, "spatialCoverage"] = -100
                dataDf.at[idx, "spatialCoverageForPOI1"] = -100
                dataDf.at[idx, "spatialCoverageForPOI2"] = -100
                dataDf.at[idx, "spatialCoverageForPOI3"] = -100
                dataDf.at[idx, "spatialCoverageForPop"] = -100
                bar.update()
                continue
            
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
 
            bar.set_description(f"Calculating POI and population spatial coverage of EVCS for {city:<25.25}") # <max.min
            # POI
            future = executor.submit(
                _calculatePOI, poiDf, geom, evcsBuffer
            )
            futuresPOI.append(future)
            futureDictPOI[future] = idx
            
            #Population
            if popPath is not None:
                future = executor.submit(
                    _calculatePop, popPath, geom, evcsBuffer
                )
                futuresPop.append(future)
                futureDictPop[future] = (idx, False) # idx, pop
            else:
                bar.update(0.5)

        for future in as_completed(futuresPOI):
            idx = futureDictPOI[future]
            try:
                result = future.result()
                if result is not None:
                    dataDf.at[idx, "spatialCoverageForPOI1"] = result[0]
                    dataDf.at[idx, "spatialCoverageForPOI2"] = result[3]
                    dataDf.at[idx, "spatialCoverageForPOI3"] = result[6]
                bar.update(0.5)
            except Exception as e:
                raise RuntimeError(f"Error processing POI for index {idx}: {e}")
        
        for future in as_completed(futuresPop):
            idx = futureDictPop[future]
            try:
                result = future.result()
                if result is not None:
                    dataDf.at[idx, "spatialCoverageForPop"] = result[0]
                bar.update(0.5)
            except Exception as e:
                raise RuntimeError(f"Error processing population for index {idx}: {e}")

    return

def _calculatePop(
    popPath: str,
    geom: BaseGeometry, evcsBuffer: BaseGeometry
) -> tuple[float, float, float] | None:
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
            
        # City population
        rasterCity, transformCity = mask(
            src,
            [geom],
            crop=True,
            nodata=src.nodata
        )
        rasterCity: np.ndarray = rasterCity[0]  # Assuming population data is in the first band
        validMask = ~np.isnan(rasterCity) & (rasterCity != src.nodata)
        totalPop = np.sum(rasterCity[validMask], dtype=np.float64)

        if totalPop == 0: return

        # EVCS buffer
        maskEVCS = geometry_mask(
            [evcsBuffer],
            out_shape=rasterCity.shape,
            transform=transformCity,
            invert=True
        )
        EVCSCoveredPop = np.sum(rasterCity[maskEVCS & validMask], dtype=np.float64)

        totalCover = EVCSCoveredPop / totalPop

    return totalCover, 0, 0
    # spatialCoverageForPop, spatialCoverageForPop_BuiltUp, spatialCoverageForPop_Other

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
    result = np.full([3, 3], np.nan, dtype=np.float64)
    for i in (1, 2, 3):
        cat = cityPOI["fsq_category_ids"] == i
        cityPOICategory = cityPOI[cat]

        totalPOI = cityPOICategory.shape[0]
        if totalPOI == 0: continue

        coverdPOI = inEVCS[cat].sum()
        result[i-1][0] = coverdPOI / totalPOI

    return result.flatten()
    # POI1, POI1_BuiltUp, POI1_Other, POI2, POI2_BuiltUp, POI2_Other, POI3, POI3_BuiltUp, POI3_Other