import os
import numpy as np
import rasterio as rio
from rasterio import windows, features
from shapely.geometry.base import BaseGeometry
from shapely.geometry import box

from .byCities import analysisByCities
from .spatialConcentration import __calIndex

def spatialConcentration_Country(data: analysisByCities, evcsThres: int = 10):
    df = data.cdf
    dfCrs = data.crs
    bar = data.bar("Calculating spatial concentration of EVCS", 1, countryLevel=True)
    col = "spatialConcentration"
    df[col] = np.nan

    with (
        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
        rio.open(os.path.join(data.savePath, "evcs.tif")) as src
    ):
        if dfCrs != src.crs.to_epsg(): df = df.to_crs(src.crs)

        # Filter outside data
        rasterPoly = box(*src.bounds)
        dfFiltered = df[df.geometry.intersects(rasterPoly)]

        for row in dfFiltered[["iso3_code", "geometry"]].itertuples():
            idx = getattr(row, "Index")
            iso3 = getattr(row, "iso3_code")
            geom: BaseGeometry = getattr(row, "geometry")
            
            bar.set_description(f"Calculating spatial coverage of EVCS for {iso3}")

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

            countryMask = features.geometry_mask(
                [geom],
                out_shape=shape,
                transform=transform,
                invert=True,
                all_touched=False
            )

            validMask = (raster != src.nodata) & ~np.isnan(raster) & countryMask
            cityVals = raster[validMask]
            evcsNum = np.sum(cityVals)

            if evcsNum == 0:
                bar.update()
                continue
            elif evcsNum <= evcsThres:
                data.cdf.at[idx, col] = -100
                bar.update()
                continue
            
            data.cdf.at[idx, col] = __calIndex(cityVals)

            bar.update()

    bar.set_description("Saving results for \"spatialConcentration\"")
    data.updateData(
        (col, "REAL", None, False),
        countryLevel=True
    )
    bar.n = bar.total
    bar.refresh()
    bar.close()

    return