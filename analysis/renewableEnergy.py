import os
import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio.mask import mask
from tqdm import tqdm
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
from typing import Any

from .byCities import analysisByCities

def renewableEnergy(
    data: analysisByCities,
    evcs: str, evcsThres: int = 10
) -> None:
    dataDf = data.df
    bar = data.bar("Calculating spatial coverage of EVCS", 1)
    col = "solar_1"
    dataDf[col] = np.nan
    col2 = "wind_1"
    dataDf[col2] = np.nan

    evcsDf = gpd.read_file(evcs, layer="evcs", encoding="utf-8").geometry

    with rio.open(os.path.join(data.savePath, "GHI", "GHI.tif"), options=["NUM_THREADS=ALL_CPUS"]) as srcSolar:
        with rio.open(os.path.join(data.savePath, "wind_speed_cog_10m.tif"), options=["NUM_THREADS=ALL_CPUS"]) as srcWind:
            if evcsDf.crs is None or evcsDf.crs.to_epsg() != srcSolar.crs.to_epsg() or evcsDf.crs.to_epsg() != srcWind.crs.to_epsg():
                raise RuntimeError("Incorrect projection.")
            
            __process(dataDf, evcsDf, evcsThres, srcSolar, srcWind, bar)

    bar.set_description("Saving results for renewable energy.")
    data.updateData(
        (col, "REAL", None, False),
        (col2, "REAL", None, False)
    )
    bar.update()
    bar.close()

    return

def __process(
    dataDf: gpd.GeoDataFrame, evcsDf: gpd.GeoSeries, evcsThres: int,
    srcSolar: Any, srcWind: Any,
    bar: tqdm
) -> None:
    solarPoly = box(*srcSolar.bounds)
    windPoly = box(*srcWind.bounds)

    for row in dataDf[["disp_en", "geometry"]].itertuples():
        idx = getattr(row, "Index")
        city = getattr(row, "disp_en")
        geom: BaseGeometry = getattr(row, "geometry")

        bar.set_description(f"Calculating renewable energy for {city:<25.25}") # <max.min
        evcs = evcsDf[evcsDf.intersects(geom)]

        if evcs.shape[0] <= evcsThres:
            dataDf.at[idx, "solar_1"] = -100
            dataDf.at[idx, "wind_1"] = -100
            bar.update()
            continue
        
        if geom.intersects(solarPoly):
            dataDf.at[idx, "solar_1"] = __processRaster(srcSolar, geom, evcs)
        if geom.intersects(windPoly):
            dataDf.at[idx, "wind_1"] = __processRaster(srcWind, geom, evcs)

        bar.update()

    return

def __processRaster(src: Any, geom: BaseGeometry, evcs: gpd.pd.Series) -> float:
    raster: np.ndarray
    raster, _ = mask(
        src,
        [geom],
        crop=True,
        all_touched=True,
        nodata=src.nodata
    )

    raster = raster[0]
    validMask = (raster != src.nodata) & (~np.isnan(raster))
    raster = raster[validMask]

    if not validMask.any():
        return np.nan

    # top 25%
    threshold = np.percentile(raster, 75)
    coords = [(p.x, p.y) for p in evcs.geometry]
    values = np.array([val[0] for val in src.sample(coords)])
    values = values[(values != src.nodata) & (~np.isnan(values))]
    top25 = np.sum(values >= threshold) / evcs.shape[0]
    
    return top25