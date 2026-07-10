import os
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.mask import mask
from rasterio.transform import rowcol
from shapely.geometry import box
from tqdm import tqdm

from __plot import plt, BAR_COLORS
from .byCities import analysisByCities

def gini(
    data: analysisByCities,
    pop: str,
    evcs: str, evcsThres: int = 10
) -> None:
    dataDf = data.df
    bar = data.bar("Calculating spatial accessibility gini of EVCS", 1, 7)
    cols = (
        "gini",
        "gini_male", "gini_female",
        "gini_child", "gini_young", "gini_middle", "gini_elder"
    )
    for col in cols:
        dataDf[col] = np.nan

    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["level1", "geometry"]]

    if dataDf.crs != evcsDf.crs:
        raise RuntimeError("EVCS do not have same projection with `data`.")

    for iso3, countryDf in dataDf[["iso3_code", "disp_en", "geometry"]].groupby("iso3_code"):
        assert isinstance(countryDf, gpd.GeoDataFrame)
        bar.set_postfix(iso3=iso3)

        popPaths = (
            os.path.join(
                pop,
                "population_All",
                "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_Male",
                "{}_['m']_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_Female",
                "{}_['f']_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_children",
                "{}_allGender_[0, 1, 5, 10, 15]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_young",
                "{}_allGender_[20, 25, 30, 35, 40]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_middle",
                "{}_allGender_[45, 50, 55]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_elderly",
                "{}_allGender_[60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            )
        )

        if not os.path.exists(popPaths[0]):
            bar.update(countryDf.shape[0] * 7)
            continue
        
        subEVCSDf = evcsDf.loc[evcsDf["level1"] == iso3].geometry

        for i, popPath in enumerate(popPaths):
            __processByCountry(
                dataDf,
                countryDf,
                subEVCSDf, evcsThres,
                popPath,
                bar, os.path.join(data.savePath, "lorenz", str(iso3)), cols[i]
            )
    
    bar.set_description("Saving results for gini coefficient")
    data.updateData(
        (cols[0], "REAL", None, False),
        (cols[1], "REAL", None, False),
        (cols[2], "REAL", None, False),
        (cols[3], "REAL", None, False),
        (cols[4], "REAL", None, False),
        (cols[5], "REAL", None, False),
        (cols[6], "REAL", None, False)
    )
    bar.update()
    bar.close()
    
    return

def __processByCountry(
        dataDf: gpd.GeoDataFrame,
        countryDf: gpd.GeoDataFrame,
        subEVCSDf: gpd.GeoSeries, evcsThres: int,
        popPath: str,
        bar: tqdm, lorSave: str, subName: str
) -> None:
    os.makedirs(lorSave, exist_ok=True)
    suffix = "" if subName == "gini" else "_{}".format(subName)

    with (
        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
        rio.open(popPath) as src
    ):
        if dataDf.crs is None or dataDf.crs.to_epsg() != src.crs.to_epsg():
            raise RuntimeError("Population raster do not have same projection with `data`.")
        
        rasterBound = box(*src.bounds)
        
        for row in countryDf[["disp_en", "geometry"]].itertuples():
            idx = getattr(row, "Index")
            city = getattr(row, "disp_en").replace('/', '_')
            geom = getattr(row, "geometry")

            bar.set_description(f"Calculating spatial coverage of EVCS for {city:<25.25}") # <max.min

            if not geom.intersects(rasterBound):
                bar.update()
                continue

            evcsGeoSub = subEVCSDf[subEVCSDf.intersects(geom)]
            if evcsGeoSub.shape[0] <= evcsThres:
                dataDf.at[idx, subName] = -100
                bar.update()
                continue

            pop: np.ndarray
            pop, popTransform = mask(
                src,
                [geom],
                crop=True,
                all_touched=True,
                nodata=src.nodata
            )
            pop = pop[0]

            valid = ~np.isnan(pop) & (pop != src.nodata)
            if not np.any(valid):
                # 无有效数据，跳过
                bar.update()
                continue
        
            popValid = pop[valid]
            # No corresponding raster data in the boundary
            if np.nansum(popValid) == 0:
                bar.update()
                continue

            # # DPhigh = np.max(pop)
            # # DPlow = np.min(pop)
            # # diff = DPhigh - DPlow

            XCoords = evcsGeoSub.x.to_numpy() # type: ignore
            YCoords = evcsGeoSub.y.to_numpy() # type: ignore
            # coords = np.column_stack((XCoords, YCoords))
            # # values = np.array([(val[0] - DPlow) / diff if val[0] != src.nodata else 0 for val in src.sample(coords)])
            # values = np.array([val[0] if val[0] != src.nodata else 0 for val in src.sample(coords)])

            # Get raster results
            ## Get corresponding row and col index
            # rows, cols = rowcol(src.transform, XCoords, YCoords)
            # idxs = np.ravel_multi_index((rows, cols), src.shape)
            # raster = pd.DataFrame({"values": values, "idxs": idxs}).dropna()
            # raster = raster.groupby(by="idxs").agg(
            #     evcs=("idxs", "count"),
            #     value=("values", "first")
            # ).sort_values(
            #     by=["value", "evcs"], ascending=[False, True]
            # )
            # raster.to_csv(
            #     os.path.join(lorSave, f"{city}{suffix}.csv"),
            #     encoding="utf-8",
            #     index=False
            # )

            # 统计每个像素的EVCS数量
            rows, cols = rowcol(popTransform, XCoords, YCoords)
            rows = np.clip(rows, 0, pop.shape[0] - 1)
            cols = np.clip(cols, 0, pop.shape[1] - 1)
            flatIdx = np.ravel_multi_index((rows, cols), pop.shape)
            counts = np.bincount(flatIdx, minlength=pop.size).reshape(pop.shape)

            # raster = pd.DataFrame({
            #     "value": pop, "evcs": counts[valid]
            # }).dropna().sort_values(
            #     by=["value", "evcs"], ascending=[False, True]
            # )
            raster = pd.DataFrame({
                "value": popValid, "evcs": counts[valid]
            }).dropna()
            conditions = [
                raster["value"] == 0,
                (raster["value"] != 0) & (raster["evcs"] == 0),
                (raster["value"] != 0) & (raster["evcs"] != 0)
            ]
            choices = [
                0,
                np.inf,
                raster["value"] / raster["evcs"]
            ]
            raster["pre_cap"] = np.select(conditions, choices, default=np.nan)
            raster = raster.sort_values(
                by=["pre_cap"], ascending=[False]
            ).drop(columns=["pre_cap"])
            raster.to_csv(
                os.path.join(lorSave, f"{city}{suffix}.csv"),
                encoding="utf-8",
                index=False
            )

            dataDf.at[idx, subName] = _gini(
                raster["value"].to_numpy(), raster["evcs"].to_numpy(),
                lorSave, f"{city}{suffix}"
            )

            bar.update()

    return

def _gini(
    indicator: np.ndarray, evcs:np.ndarray,
    savePath: str, city: str, sorted: bool = True
) -> float:
    # Special case: if only one grid cell has nonzero indicatior
    # Return nan if total count less than 10, because no significant meaning for gini
    if np.count_nonzero(evcs) <= 10: return -100

    # Sort values by EVCS in ascending order
    if not sorted:
        raise RuntimeError()
        # sortedIndices = np.lexsort((-indicator, evcs))
        # sortedIndicator = indicator[sortedIndices]
        # sortedEVCS = evcs[sortedIndices]
    else:
        sortedIndicator = indicator
        sortedEVCS = evcs

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
    gini = np.float64(1 - 2 * np.trapezoid(cumEVCS, cumIndicator))

    # Plot lorenz curve
    _, ax = plt.figure("D")
    ax.plot(
        cumIndicator, cumEVCS,
        label="Lorenz curve",
        color=BAR_COLORS[0][1]
    )
    ax.plot([0, 1], [0, 1], label="Equality line", linestyle="--", color="gray")
    ax.set_title(f"{gini:.4f}")
    plt.xlabel("Cumulative share of population")
    plt.ylabel("Cumulative share of EVCS")
    plt.plot(savePath, "{}.jpg".format(city), bbox_inches="tight")

    # Compute the Gini coefficient using the trapezoidal rule (Lorenz curve area)
    return gini