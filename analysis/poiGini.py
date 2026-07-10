import os
import rasterio as rio
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry.base import BaseGeometry
from rasterio.transform import rowcol

from __setting import checkCRS
from .byCities import analysisByCities

def poiGini(
    data: analysisByCities,
    pop: str, poi: str,
    evcs: str, evcsThres: int = 10,
    maxThread: int = 1
) -> None:
    dataDf = data.df
    bar = data.bar("Calculating gini of EVCS", 1, 2)
    cols = (
        "gini_poi1", "gini_poi2", "gini_poi3"
    )
    for col in cols:
        dataDf[col] = np.nan

    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["level1", "geometry"]]
    checkCRS(evcsDf, dataDf)
    poiDf = gpd.read_parquet(poi, filters=[("fsq_category_ids", "in", [1, 2, 3])])
    checkCRS(poiDf, dataDf)

    # futures = []
    # futuresDict = {}
    # with ProcessPoolExecutor(max_workers=maxThread) as excutor:
        # for iso3, countryDf in dataDf[["iso3_code", "disp_en", "geometry"]].groupby("iso3_code"):
        #     countryDf = gpd.GeoDataFrame(countryDf.drop(columns="iso3_code"), geometry="geometry", crs=dataDf.crs)
        #     bar.set_postfix(iso3=iso3)

        #     subEVCSDf = evcsDf.loc[evcsDf["level1"] == iso3]
        #     subPOIDf = poiDf.loc[poiDf["level1"] == iso3]
        #     popPaths = os.path.join(
        #         pop,
        #         "population_All",
        #         "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
        #     )

        #     if os.path.exists(popPaths):
        #         future = excutor.submit(_calOneUnitByRaster, countryDf, popPaths, subPOIDf, subEVCSDf, evcsThres)
        #         futures.append(future)
        #         futuresDict[future] = iso3

        #     bar.update(countryDf.shape[0])

        # for future in as_completed(futures):
        #     unit = futuresDict[future]
        #     try:
        #         result: pd.DataFrame = future.result()
        #     except Exception as e:
        #         raise RuntimeError("{}: {}".format(unit, e))
        #     else:
        #         bar.set_description("{} finished".format(unit))
        #         dataDf.loc[result.index, cols] = result.values
        #         bar.update(result.shape[0])

    for iso3, countryDf in dataDf[["iso3_code", "disp_en", "geometry"]].groupby("iso3_code"):
        countryDf = gpd.GeoDataFrame(countryDf.drop(columns="iso3_code"), geometry="geometry", crs=dataDf.crs)
        bar.set_postfix(iso3=iso3)

        subEVCSDf = evcsDf.loc[evcsDf["level1"] == iso3]
        subPOIDf = poiDf.loc[poiDf["level1"] == iso3]
        popPaths = os.path.join(
            pop,
            "population_All",
            "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
        )

        if os.path.exists(popPaths):
            result = _calOneUnitByRaster(countryDf, popPaths, subPOIDf, subEVCSDf, evcsThres)

            bar.set_description("{} finished".format(iso3))
            dataDf.loc[result.index, cols] = result.values
        bar.update(countryDf.shape[0]*2)

    data.updateData(
        (cols[0], "REAL", None, False),
        (cols[1], "REAL", None, False),
        (cols[2], "REAL", None, False)
    )
    bar.update()
    bar.close()

    return
    
def _calOneUnitByRaster(
    countryDf: gpd.GeoDataFrame,
    rasterPath: str, poiGeo: gpd.GeoDataFrame,
    evcsGeo: gpd.GeoDataFrame,
    evcsThres: int
) -> pd.DataFrame:
    n = countryDf.shape[0]
    countryResults = np.full([n, 3], np.nan, dtype=np.float64)
    cityid = np.empty(n, dtype=np.int64)

    with rio.open(rasterPath, options=["NUM_THREADS=ALL_CPUS"]) as src:
        for i, row in enumerate(countryDf.itertuples()):
            cityid[i] = getattr(row, "Index")
            boundary: BaseGeometry = getattr(row, "geometry")

            # Get evcs points
            possibleMAtch = np.array(evcsGeo.sindex.intersection(boundary.bounds), dtype=np.int64)
            evcsGeoSub = evcsGeo.iloc[possibleMAtch]
            evcsGeoSub = evcsGeoSub[evcsGeoSub.intersects(boundary)]

            if evcsGeoSub.shape[0] == 0:
                continue
            elif evcsGeoSub.shape[0] < evcsThres:
                countryResults[i, 0] = -100
                countryResults[i, 1] = -100
                countryResults[i, 2] = -100
                continue

            # Get poi
            possibleMAtch = np.array(poiGeo.sindex.intersection(boundary.bounds), dtype=np.int64)
            poiGeoSub = poiGeo.iloc[possibleMAtch]
            poiGeoSub = poiGeoSub[poiGeoSub.intersects(boundary)]

            # Change evcs to raster
            PopXCoords = evcsGeoSub.geometry.x.to_numpy().astype(np.float32)
            PopYCoords = evcsGeoSub.geometry.y.to_numpy().astype(np.float32)
            rows, cols = rowcol(src.transform, PopXCoords, PopYCoords)
            valid = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
            rows = rows[valid]
            cols = cols[valid]
            EVCSIdxs = np.ravel_multi_index((rows, cols), src.shape)
            evcsAgg = pd.DataFrame({"idx": EVCSIdxs}).groupby("idx", as_index=False).size().rename(columns={"size": "evcs"})

            for ids, subPOI in poiGeoSub.groupby("fsq_category_ids"):
                x = int(np.asarray(ids).item()) - 1
                # No corresponding POI data in the boundary
                if subPOI.shape[0] == 0:
                    continue

                # Change poi to raster
                XCoords = subPOI.geometry.x.to_numpy().astype(np.float32)
                YCoords = subPOI.geometry.y.to_numpy().astype(np.float32)
                rows, cols = rowcol(src.transform, XCoords, YCoords)
                valid = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
                rows = rows[valid]
                cols = cols[valid]
                poiIdxs = np.ravel_multi_index((rows, cols), src.shape)
                poiAgg = pd.DataFrame({"idx": poiIdxs}).groupby("idx", as_index=False).size().rename(columns={"size": "poi"})
                raster = evcsAgg.merge(poiAgg, on="idx", how="left")
                raster["poi"] = raster["poi"].fillna(0)

                DPhigh = raster["poi"].max()
                DPlow = raster["poi"].min()
                diff = DPhigh - DPlow
                raster["poi"] = (raster["poi"] - DPlow) / diff if diff != 0 else 1

                countryResults[i, x] = _gini(raster["poi"].to_numpy(), raster["evcs"].to_numpy())

    return pd.DataFrame(countryResults, index=cityid, columns=["gini_poi1", "gini_poi2", "gini_poi3"])

def _gini(indicator: np.ndarray, evcs:np.ndarray) -> float:
    if np.count_nonzero(evcs) <= 10: return -100

    # Sort values by EVCS in ascending order
    sortedIndices = np.lexsort((-indicator, evcs))
    sortedIndicator = indicator[sortedIndices]
    sortedEVCS = evcs[sortedIndices]

    # Compute cumulative EVCS and cumulative indicatior
    totalIndicator = sortedIndicator.sum()
    if totalIndicator == 0: return 0
    totalEVCS = sortedEVCS.sum()

    # Normalize cumulative EVCS and indicatior (range 0–1)
    cumIndicator = np.cumsum(sortedIndicator) / totalIndicator
    cumEVCS = np.cumsum(sortedEVCS) / totalEVCS
    ## Add 0
    lack0 = cumIndicator[0] != 0 or cumEVCS[0] != 0
    cumIndicator = np.insert(cumIndicator, 0, 0) if lack0 else cumIndicator 
    cumEVCS = np.insert(cumEVCS, 0, 0) if lack0 else cumEVCS

    # Compute the Gini coefficient using the trapezoidal rule (Lorenz curve area)
    return np.float64(1 - 2 * np.trapezoid(cumEVCS, cumIndicator))