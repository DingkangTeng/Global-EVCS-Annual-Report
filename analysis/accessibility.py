import os
import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio as rio
from rasterio import features, windows
from shapely.geometry.base import BaseGeometry
from typing import Any

from __setting import stdCityName
from .byCities import analysisByCities

class accessibility:
    __slots__ = ["df", "bar"]

    __COLS = (
        "acc1km_percentage",
        "acc1km_percentage_male", "acc1km_percentage_female",
        "acc1km_percentage_child", "acc1km_percentage_young", "acc1km_percentage_middle", "acc1km_percentage_elder",
        "acc1km_percentage_BuiltUp", "acc1km_percentage_Other"
    )
    
    def __init__(self, data: analysisByCities, pop: str, savePath: str, interval: int = 1000) -> None:
        self.df = data.df
        for col in self.__COLS:
            self.df[col] = np.nan

        savePath = os.path.join(savePath, "accessibility")
        self.bar = data.bar("Analysising accessibility", 1, 7)
        builtUpAll = gpd.read_file(data.builtup, layer="builtup", columns=["iso3", "geometry"])
        if builtUpAll.crs is not None and builtUpAll.crs.to_epsg() != 4326:
            builtUpAll = builtUpAll.to_crs(4326)
        elif builtUpAll.crs is None:
            raise RuntimeError("Input built-up area data do not have CRS.")

        # Process by country group
        for iso3, countryDf in self.df[["iso3_code", "disp_en", "geometry"]].groupby("iso3_code"):
            countryDf = gpd.GeoDataFrame(countryDf, crs=data.crs)
            self.bar.set_postfix(iso3=iso3)

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
                self.bar.update(countryDf.shape[0] * 7)
                continue

            accPath = os.path.join(savePath, str(iso3))
            countryResult = os.path.join(accPath, "{}.csv".format(iso3))

            # Have population raster, accessibility raster, and do not have conuntry level result
            if os.path.exists(accPath) and not os.path.exists(countryResult):
                results = []
                for i, popPath in enumerate(popPaths):
                    # Get builtup area for specific country
                    if i == 0:
                        builtUp = gpd.GeoSeries(builtUpAll[builtUpAll["iso3"] == iso3].geometry)
                    else:
                        builtUp = None

                    with (
                        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
                        rio.open(popPath) as src
                    ):
                        results.append(
                            self.__processByCountry(
                                countryDf, self.__COLS[i], accPath, src, interval,
                                i == 0, builtUp
                            )
                        )
                accCountry = pd.concat(results, axis=1)
                if not accCountry.empty:
                    accCountry.to_csv(countryResult, encoding="utf-8", index_label="accessibility")
            
            else:
                self.bar.update(countryDf.shape[0] * 7)
        
        self.bar.set_description("Saveing percentage for population who has EVCS within 1 km.")
        data.updateData(
            (self.__COLS[0], "Real", None, False),
            (self.__COLS[1], "Real", None, False),
            (self.__COLS[2], "Real", None, False),
            (self.__COLS[3], "Real", None, False),
            (self.__COLS[4], "Real", None, False),
            (self.__COLS[5], "Real", None, False),
            (self.__COLS[6], "Real", None, False),
            (self.__COLS[7], "Real", None, False),
            (self.__COLS[8], "Real", None, False)
        )
        self.bar.update()
        self.bar.close()

        return

    def __processByCountry(
        self,
        df: gpd.GeoDataFrame, col: str,
        accPath: str, src: Any,
        interval: int,
        calUrbanArea: bool, builtUpAll: gpd.GeoSeries | None = None
    ) -> pd.DataFrame:
        # Unify projection
        crs = src.crs
        if crs.to_epsg() != 4326:
            raise RuntimeError("Input population data is not WGS84")
        if df.crs is not None and df.crs.to_epsg() != 4326:
            df.to_crs(4326, inplace=True)
        elif df.crs is None:
            raise RuntimeError("Input data do not have CRS.")
        
        rows, cols = src.height, src.width
        transform = src.transform
        nodata = src.nodata
        
        countryResult = np.empty(df.shape[0], dtype=object)
        i = 0

        for row in df[["disp_en", "geometry"]].itertuples():
            idx = getattr(row, "Index")
            city = getattr(row, "disp_en")
            geom: BaseGeometry = getattr(row, "geometry")
            stdName = stdCityName(city)
            tifPath = os.path.join(accPath, "{}.tif".format(stdName))
            belowThres = os.path.join(accPath, "{}.txt".format(stdName))

            # Skip no accessibility data country
            if os.path.exists(belowThres):
                self.df.at[idx, col] = -100
                self.bar.update()
                continue
            elif not os.path.exists(tifPath):
                self.bar.update()
                continue

            self.bar.set_description(f"Calculating spatial coverage of EVCS for {city:<25.25}") # <max.min

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

            # No population in the city, skip
            if not np.any(validMask):
                self.bar.update()
                continue

            popArray = popArray[validMask]

            with rio.open(tifPath, options=["NUM_THREADS=ALL_CPUS"]) as srcAcc:
                accArray = srcAcc.read(1)
                accArray = accArray[validMask]
                if np.isnan(accArray).all():
                    self.bar.update()
                    continue
                shape = popArray.shape

                if accArray.shape != shape:
                    raise RuntimeError(
                        f"Shape mismatch: popArray shape {shape}, "
                        f"accArray shape {accArray.shape}. "
                        "Ensure both rasters have the same resolution and alignment."
                    )

                # Calculate built up
                if calUrbanArea:
                    assert builtUpAll is not None

                    possibleMatch = builtUpAll.sindex.intersection(geom.bounds)
                    if possibleMatch.size > 0:
                        builtUp = gpd.GeoSeries(builtUpAll.iloc[possibleMatch])
                        builtUp = builtUp[builtUp.intersects(geom)]
                    else:
                        builtUp = gpd.GeoSeries([])

                    if len(builtUp) == 0:
                        builtupMask = np.full(popArray.shape, False, dtype=bool)
                        popArrayBuilt = np.full(popArray.shape, 0, dtype=popArray.dtype)
                        popArrayOther = popArray
                    else:
                        builtUp = builtUp.union_all() # type: ignore
                        builtupMask = features.geometry_mask(
                            [geom.intersection(builtUp)],
                            out_shape=(windowH, windowW),
                            transform=windowTransform,
                            invert=True,
                            all_touched=False
                        )
                        builtupMask = builtupMask[validMask]
                        popArrayBuilt = popArray * builtupMask
                        popArrayOther = popArray * (~builtupMask)

                    popCol =  [
                        "population_{}".format(col),
                        "population_{}_BuiltUp".format(col),
                        "population_{}_Other".format(col)
                    ]
                    result = pd.DataFrame({
                        "accessibility": np.round(accArray, 2),
                        popCol[0]: np.round(popArray, 2),
                        popCol[1]: np.round(popArrayBuilt, 2),
                        popCol[2]: np.round(popArrayOther, 2),
                    })
                    
                else:
                    popCol = ["population_{}".format(col)]
                    result = pd.DataFrame({
                        "accessibility": np.round(accArray, 2),
                        popCol[0]: np.round(popArray, 2),
                    })
            
            countryResult[i] = result.set_index("accessibility")
            i += 1

            # City level result
            result["distance"] = self.__group(result, interval)
            result = result.groupby(
                by="distance", observed=False
            )[popCol].sum().reset_index().sort_values(
                by="distance"
            )

            for j, c in enumerate(popCol):
                total = result[c].sum()
                result[f"population_percent_{j}"] = 100 * result[c] / total

                result[f"cumulate_population_{j}"] = result[c].cumsum()
                result[f"cumulative_percent{j}"] = 100 * result[f"cumulate_population_{j}"] / total

            # Save result to boundary geodata
            self.df.at[idx, col] = result.at[0, "population_percent_0"]
            if calUrbanArea:
                self.df.at[idx, "acc1km_percentage_BuiltUp"] = result.at[0, "population_percent_1"]
                self.df.at[idx, "acc1km_percentage_Other"] = result.at[0, "population_percent_2"]
            
            self.bar.update()

        if i > 0:
            combined = pd.concat(countryResult[:i])
            combined = combined.groupby(combined.index).sum()
        else:
            combined = pd.DataFrame()

        return combined

    @staticmethod
    def __group(result: pd.DataFrame, interval: int = 1000) -> pd.Series:
            bins = np.arange(0, result["accessibility"].max() + interval, interval)
            
            return pd.cut(
                result["accessibility"],
                bins=bins,
                right=False, # Left closed, right open
                labels=[int(b) for b in bins[1:]]
            )