import os
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.mask import mask
from rasterio.transform import rowcol
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
from typing import Any

from .byCities import analysisByCities
from .gini import _gini

def gini_Country(
    data: analysisByCities,
    pop: str,
    evcs: str, evcsThres: int = 10
) -> None:
    dataDf = data.cdf
    bar = data.bar("Calculating spatial accessibility gini of EVCS", 1, countryLevel=True)
    col ="gini"
    dataDf[col] = np.nan

    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8")[["level1", "geometry"]]

    if dataDf.crs != evcsDf.crs:
        raise RuntimeError("EVCS do not have same projection with `data`.")

    for row in dataDf[["iso3_code", "geometry"]].itertuples():
        idx = getattr(row, "Index")
        iso3 = getattr(row, "iso3_code")
        geom = getattr(row, "geometry")
        # if iso3 != "HKG": continue # debug
        bar.set_postfix(iso3=iso3)

        popPath = pop # API interfce
        subEVCSDf = evcsDf.loc[evcsDf["level1"] == iso3].geometry

        __processByCountry(
            dataDf, iso3,
            idx, geom,
            subEVCSDf, evcsThres,
            popPath,
            os.path.join(data.savePath, "lorenz", str(iso3))
        )
        bar.update()
    
    bar.set_description("Saving results for gini coefficient")
    data.updateData(
        (col, "REAL", None, False),
        countryLevel=True
    )
    bar.update()
    bar.close()
    
    return

def __processByCountry(
        dataDf: gpd.GeoDataFrame, iso3: str,
        idx: Any, geom: BaseGeometry,
        subEVCSDf: gpd.GeoSeries, evcsThres: int,
        popPath: str,
        lorSave: str
) -> None:
    os.makedirs(lorSave, exist_ok=True)

    with (
        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
        rio.open(popPath) as src
    ):
        if dataDf.crs is None or dataDf.crs.to_epsg() != src.crs.to_epsg():
            raise RuntimeError("Population raster do not have same projection with `data`.")
        
        rasterBound = box(*src.bounds)

        if not geom.intersects(rasterBound):
            return

        evcsGeoSub = subEVCSDf[subEVCSDf.intersects(geom)]
        if evcsGeoSub.shape[0] <= evcsThres:
            dataDf.at[idx, "gini"] = -100
            return

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
            return

        popValid = pop[valid]
        # No corresponding raster data in the boundary
        if np.nansum(popValid) == 0:
            return

        XCoords = evcsGeoSub.x.to_numpy() # type: ignore
        YCoords = evcsGeoSub.y.to_numpy() # type: ignore

        # Count the number of EVCSs for each pixel
        rows, cols = rowcol(popTransform, XCoords, YCoords)
        rows = np.clip(rows, 0, pop.shape[0] - 1)
        cols = np.clip(cols, 0, pop.shape[1] - 1)
        flatIdx = np.ravel_multi_index((rows, cols), pop.shape)
        counts = np.bincount(flatIdx, minlength=pop.size).reshape(pop.shape)

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
            os.path.join(lorSave, f"{iso3}_CountryLevel.csv"),
            encoding="utf-8",
            index=False
        )

        dataDf.at[idx, "gini"] = _gini(
            raster["value"].to_numpy(), raster["evcs"].to_numpy(),
            lorSave, f"{iso3}_CountryLevel"
        )

    return