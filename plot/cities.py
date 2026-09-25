import os
import geopandas as gpd
import pandas as pd
import numpy as np
# from matplotlib.patches import Patch
from typing import Self

from __setting import EUR, CHN, ASEAN, getUtmZone, CHN_ALBERS, ASIA_N_LAMBERT, IBGE_ALBERS
from __plot import plt, BAR_COLORS, LABEL_SIZE, plotSet
from analysis import analysisByCities
from .__globalPlot import globalPlot
from .__constant import HAWAII, ALASKA
from .__template import mapTemplate, baseTemplate
from .__text import _ISO3

class plotCities(mapTemplate, baseTemplate):
    __slots__ = [
        "data",
        "level1", "level2", "mainCities", "dashline",
        "savePath"
    ]

    __COLS_STD_NAME = {
        "spatialConcentration": "spatial_concentration",
        "spatialCoverage": "spatial_coverage_evcs",
        "spatialCoverageForPOI1": "spatial_coverage_public_facility",
        "spatialCoverageForPOI2": "spatial_coverage_commercial_facility",
        "spatialCoverageForPOI3": "spatial_coverage_leasure_facility",
        "spatialCoverageForPop": "spatial_coverage_population",
        "acc1km_percentage": "accessibility_1km"
    }
    
    def __init__(
        self,
        data: analysisByCities, mapElement: str, savePath: str,
        language: baseTemplate.LANGUAGE = "zh"
    ) -> None:
        baseTemplate.__init__(self, language)

        self.data = data

        # Fig save path
        self.savePath = os.path.join(savePath, "fig_{}".format(language))
        os.makedirs(self.savePath, exist_ok=True)

        self.level1 = gpd.read_file(data.boundary, layer="level1", encoding="utf-8")
        self.level2 = gpd.read_file(data.boundary, layer="level2", encoding="utf-8")
        self.mainCities = gpd.read_file(mapElement, layer="mainCities", encoding="utf-8")
        self.dashline = (
            gpd.read_file(mapElement, layer="JDX", encoding="utf-8").geometry.to_crs(CHN_ALBERS),
            gpd.read_file(mapElement, layer="JDX_sansha", encoding="utf-8").geometry.to_crs(CHN_ALBERS)
        )

        return
    
    def drawOverall(self) -> Self:
        plotSet()
        plt.setLanguage(self.language)
        # Country level
        cols = list(("spatialCoverage",) + self.slc)
        df = self.data.cdf[["iso3_code"] + cols].replace(
            -100, np.nan
        ).dropna(how="all").set_index("iso3_code")
        df["spatialConcentration"] = np.nan

        # Add city level data
        citydf = self.data.df[["iso3_code", "spatialConcentration"]].replace(
            -100, np.nan
        ).dropna(how="all")
        for iso3, subdf in citydf.groupby("iso3_code"):
            m = subdf["spatialConcentration"].median()
            df.at[iso3, "spatialConcentration"] = m

        plot = globalPlot(self.language, self.savePath)
        # Global hbar
        plot.hbar(df, cols)

        # heatmap
        plot.heat(df, ["spatialCoverageForPOI1", "spatialCoverageForPOI2", "spatialCoverageForPOI3"], lang=self.language)
        # plot.heat(df, list(self.slcGini), False) # Do not need Gini at present

        return self

    def draw(self, columnName: str, iso3: str | list[str] | set[str] = "Global") -> Self:
        plotSet()
        plt.setLanguage(self.language)

        if columnName not in self.cols:
            raise ValueError(f"'{columnName}' do not exists. Please use: {self.cols}")
        
        df = self.data.df[["iso3_code", "disp_en", "geometry", columnName]].dropna()
        mask = df[columnName] == -100
        dfInvalid = df[mask]
        df = df[~mask]
        del mask

        hawaii = gpd.GeoDataFrame()
        hawaiiInvalid = gpd.GeoDataFrame()
        alaska = gpd.GeoDataFrame()
        alaskaInvalid = gpd.GeoDataFrame()
        dfBRA = gpd.GeoDataFrame()
        dfInvalidBRA = gpd.GeoDataFrame()
        level1BRA = gpd.GeoSeries()
        level2BRA = gpd.GeoSeries()
        mainCitiesBRA = gpd.GeoDataFrame()
        dfMEX = gpd.GeoDataFrame()
        dfInvalidMEX = gpd.GeoDataFrame()
        level1MEX = gpd.GeoSeries()
        level2MEX = gpd.GeoSeries()
        mainCitiesMEX = gpd.GeoDataFrame()

        # Initial data
        ## For multi countries in one map
        if isinstance(iso3, list) or isinstance(iso3, set):
            savePath = os.path.join(self.savePath, "_".join(iso3))
            df = df[df["iso3_code"].isin(iso3)].drop(columns="iso3_code")
            df["color"], colorMapping = self.__colorCategory(columnName, df)
            level1 = self.level1[self.level1["iso3_code"].isin(iso3)].geometry
            level2 = self.level2[self.level2["iso3_code"].isin(iso3)].geometry
            mainCities = self.mainCities[self.mainCities["level1"].isin(iso3)][
                ["level3", "geometry"]
            ]

        elif iso3 == "Global":
            savePath = os.path.join(self.savePath, "Global")
            df = df.to_crs(3857) # WGS 1984 Web Mercator (auxiliary sphere)
            dfInvalid = dfInvalid.to_crs(3857)
            df["color"], colorMapping = self.__colorCategory(columnName, df)
            level1 = self.level1.geometry.to_crs(3857)
            level2 = self.level2.geometry.to_crs(3857)
            mainCities = self.mainCities[["level3", "geometry"]].to_crs(3857)

        elif iso3 in {"EUR", "ASEAN", "JPN&KOR", "AUS&NZL"}:
            savePath = os.path.join(self.savePath, iso3)
            crs = (
                3035 if iso3 == "EUR" else # ETRS89-LAEA
                27703 if iso3 == "ASEAN" else # WGS 84 / Equi7 Asia
                ASIA_N_LAMBERT if iso3 == "JPN&KOR" else # Asia North Lambert Conformal Conic
                3577 # GDA94 / Australian Albers
            )
            region = (
                EUR if iso3 == "EUR" else
                ASEAN if iso3 == "ASEAN" else
                {"JPN", "KOR"} if iso3 == "JPN&KOR" else
                {"AUS", "NZL"}
            )
            df = df[df["iso3_code"].isin(region)].drop(columns="iso3_code").to_crs(crs)
            dfInvalid = dfInvalid[dfInvalid["iso3_code"].isin(region)].drop(columns="iso3_code").to_crs(crs)
            df["color"], colorMapping = self.__colorCategory(columnName, df)
            level1 = self.level1[self.level1["iso3_code"].isin(region)].geometry.to_crs(crs)
            level2 = self.level2[self.level2["iso3_code"].isin(region)].geometry.to_crs(crs)
            mainCities = self.mainCities[self.mainCities["level1"].isin(region)][
                ["level3", "geometry"]
            ].to_crs(crs)

        # Special case for CHN
        elif iso3 == "CHN":
            savePath = os.path.join(self.savePath, "CHN")
            crs = CHN_ALBERS
            level1 = self.level1[self.level1["iso3_code"].isin(CHN)].geometry.to_crs(crs)
            level2 = self.level2[self.level2["iso3_code"].isin(CHN)].geometry.to_crs(crs)
            mainCities = self.mainCities[self.mainCities["level1"].isin(CHN)][
                ["level3", "geometry"]
            ].to_crs(crs)
            df = df[df["iso3_code"].isin(CHN)].drop(columns="iso3_code").to_crs(crs)
            dfInvalid = dfInvalid[dfInvalid["iso3_code"].isin(CHN)].drop(columns="iso3_code").to_crs(crs)
            df["color"], colorMapping = self.__colorCategory(columnName, df)

        # Special case for Global South
        elif iso3 == "GS":
            savePath = os.path.join(self.savePath, "Global South")
            # BRA
            level1BRA = self.level1[self.level1["iso3_code"] == "BRA"].geometry.to_crs(IBGE_ALBERS) # SIRGAS 2000 / Brazil Albers
            level2BRA = self.level2[self.level2["iso3_code"] == "BRA"].geometry.to_crs(IBGE_ALBERS)
            mainCitiesBRA = self.mainCities[self.mainCities["level1"] == "BRA"][
                ["level3", "geometry"]
            ].to_crs(IBGE_ALBERS)
            dfBRA = df[df["iso3_code"] == "BRA"].drop(columns="iso3_code").to_crs(IBGE_ALBERS)
            dfInvalidBRA = dfInvalid[dfInvalid["iso3_code"] == "BRA"].drop(columns="iso3_code").to_crs(IBGE_ALBERS)
            dfBRA["color"], _ = self.__colorCategory(columnName, dfBRA)

            # MEX
            level1MEX = self.level1[self.level1["iso3_code"] == "MEX"].geometry.to_crs(6372) # Mexico ITRF2008 / LCC
            level2MEX = self.level2[self.level2["iso3_code"] == "MEX"].geometry.to_crs(6372)
            mainCitiesMEX = self.mainCities[self.mainCities["level1"] == "MEX"][
                ["level3", "geometry"]
            ].to_crs(6372)
            dfMEX = df[df["iso3_code"] == "MEX"].drop(columns="iso3_code").to_crs(6372)
            dfInvalidMEX = dfInvalid[dfInvalid["iso3_code"] == "MEX"].drop(columns="iso3_code").to_crs(6372)
            dfMEX["color"], _ = self.__colorCategory(columnName, dfMEX)

            # ZAF
            level1 = self.level1[self.level1["iso3_code"] == "ZAF"].geometry.to_crs(2048) # Hartebeesthoek94 / Lo19
            level2 = self.level2[self.level2["iso3_code"] == "ZAF"].geometry.to_crs(2048)
            mainCities = self.mainCities[self.mainCities["level1"] == "ZAF"][
                ["level3", "geometry"]
            ].to_crs(2048)
            df = df[df["iso3_code"] == "ZAF"].drop(columns="iso3_code").to_crs(2048)
            dfInvalid = dfInvalid[dfInvalid["iso3_code"] == "ZAF"].drop(columns="iso3_code").to_crs(2048)
            df["color"], colorMapping = self.__colorCategory(columnName, df)
        
        # Special case for USA and USA&CAN
        elif iso3 == "USA&CAN" or iso3 == "USA":
            savePath = os.path.join(self.savePath, iso3)
            df = df[
                df["iso3_code"].isin({"USA", "CAN"}) if iso3 == "USA&CAN" else df["iso3_code"] == "USA"
            ].drop(columns="iso3_code")
            dfInvalid = dfInvalid[
                dfInvalid["iso3_code"].isin({"USA", "CAN"}) if iso3 == "USA&CAN" else dfInvalid["iso3_code"] == "USA"
            ].drop(columns="iso3_code")

            df["color"], colorMapping = self.__colorCategory(columnName, df)
            maskHA = df["disp_en"].isin(HAWAII)
            maskHAInvalid = dfInvalid["disp_en"].isin(HAWAII)
            maskAK = df["disp_en"].isin(ALASKA)
            maskAKInvalid = dfInvalid["disp_en"].isin(ALASKA)
            
            # Split Data
            crs = 5070 # NAD83
            hawaii = df[maskHA].to_crs(26904) # NAD83 / UTM zone 4N
            hawaiiInvalid = dfInvalid[maskHAInvalid].to_crs(26904)
            alaska = df[maskAK].to_crs(6393) # NAD83 (2011) Alaska Albers (Meters)
            alaskaInvalid = dfInvalid[maskAKInvalid].to_crs(6393)
            df = df[(~maskHA) & (~maskAK)].to_crs(crs)
            dfInvalid = dfInvalid[(~maskHAInvalid) & (~maskAKInvalid)].to_crs(crs)

            # Other layers
            level1 = self.level1[
                self.level1["iso3_code"].isin({"USA", "CAN"}) if iso3 == "USA&CAN" else self.level1["iso3_code"] == "USA"
            ].geometry.to_crs(crs)
            level2 = self.level2[
                self.level2["iso3_code"].isin({"USA", "CAN"}) if iso3 == "USA&CAN" else self.level2["iso3_code"] == "USA"
            ].geometry.to_crs(crs)
            mainCities = self.mainCities[
                self.mainCities["level1"].isin({"USA", "CAN"}) if iso3 == "USA&CAN" else self.mainCities["level1"] == "USA"
            ][
                ["level2", "level3", "geometry"]
            ].to_crs(crs)

        # Other countries
        else:
            savePath = os.path.join(self.savePath, iso3)
            df = df[df["iso3_code"] == iso3].drop(columns="iso3_code")
            df["color"], colorMapping = self.__colorCategory(columnName, df)
            crs = getUtmZone(df)

            level1 = self.level1[self.level1["iso3_code"] == iso3].geometry.to_crs(crs)
            level2 = self.level2[self.level2["iso3_code"] == iso3].geometry.to_crs(crs)
            mainCities = self.mainCities[self.mainCities["level1"] == iso3][
                ["level2", "level3", "geometry"]
            ].to_crs(crs)
                        
            df = df.to_crs(crs)
            dfInvalid = dfInvalid[dfInvalid["iso3_code"] == iso3].drop(columns="iso3_code").to_crs(crs)

        if df.shape[0] == 0:
            raise RuntimeError(f"No data for {iso3}")
        
        os.makedirs(savePath, exist_ok=True)

        # Histogram
        data = df[columnName].to_numpy()
        data = data if columnName in {"acc1km_percentage", "gini"} else data * 100
        figHis, axHis = plt.figure("D")
        self._plotHistogram(data, axHis, columnName, str(iso3), self.language)
        plt.plot(
            savePath, "map_{}_hist.jpg".format(self.__COLS_STD_NAME.get(columnName, columnName)),
            fig=figHis, bbox_inches="tight"
        )

        # Map
        fig, ax = plt.figure("W")

        ## Special fig for USA
        if iso3 == "USA" or iso3 == "USA&CAN":
            axAK = fig.add_axes((0.15 if iso3 == "USA" else 0.07, 0.02, 0.15, 0.15))
            axHA = fig.add_axes((0.28 if iso3 == "USA" else 0.20, 0.02, 0.15, 0.15)) 
            # Alaska
            self._plotMap(
                alaska, alaskaInvalid,
                level1.to_crs(6393), level2.to_crs(6393),
                mainCities[mainCities["level2"] == "Alaska"].to_crs(6393),
                "AK", axAK,
                frame=True,
                note={
                    "x": 0.05, "y": 0.95,
                    "text": "Alaska",
                    "ha": "left", "va": "top"
                }
            )
            # Hawaii
            self._plotMap(
                hawaii, hawaiiInvalid,
                level1.to_crs(26904), level2.to_crs(26904),
                mainCities[mainCities["level2"] == "Hawaii"].to_crs(26904),
                "HA", axHA,
                frame=True,
                note={
                    "x": 0.05, "y": 0.05,
                    "text": "Hawaii",
                    "ha": "left", "va": "bottom"
                }
            )
            mainCities = mainCities[~mainCities["level2"].isin({"Hawaii", "Alaska"})]

        ## Special figure for CHN
        elif iso3 == "CHN":
            axJDX = fig.add_axes((0.22, 0.02, 0.25, 0.25))
            self._plotMap(
                self.dashline[0], gpd.GeoSeries(),
                self.dashline[1], gpd.GeoSeries(),
                None,
                "JDX", axJDX,
                frame=True
            )
            self._plotMap(df, dfInvalid, level1, level2, None, iso3, axJDX, frame=True)
        
        # Special figure for Global South
        elif iso3 == "GS":
            axBRA = fig.add_axes((-0.6, 0, 1, 1))
            self._plotMap(
                dfBRA, dfInvalidBRA,
                level1BRA, level2BRA,
                mainCitiesBRA,
                "BRA", axBRA,
                frame=True,
                note={
                    "x": 0.05, "y": 0.95,
                    "text": _ISO3["BRA"][self.language],
                    "ha": "left", "va": "top",
                    "fontsize": LABEL_SIZE
                }
            )
            axMEX = fig.add_axes((-1.3, 0, 1, 1))
            self._plotMap(
                dfMEX, dfInvalidMEX,
                level1MEX, level2MEX,
                mainCitiesMEX,
                "MEX", axMEX,
                frame=True,
                note={
                    "x": 0.90, "y": 0.95,
                    "text": _ISO3["MEX"][self.language],
                    "ha": "left", "va": "top",
                    "fontsize": LABEL_SIZE
                }
            )

        self._plotMap(
            df, dfInvalid,
            level1, level2,
            mainCities,
            iso3, ax,
            frame=True if iso3 == "GS" else False,
            note={
                "x": 0.05, "y": 0.95,
                "text": _ISO3["ZAF"][self.language],
                "ha": "left", "va": "top",
                "fontsize": LABEL_SIZE
            } if iso3 == "GS" else None
        )

        plt.plot(
            savePath, "map_{}.jpg".format(self.__COLS_STD_NAME.get(columnName, columnName)),
            fig=fig, bbox_inches="tight"
        )
        
        return self
    
    # Drawing category
    @staticmethod
    def __colorCategory(columnName: str, df: gpd.GeoDataFrame) -> tuple[pd.Series, dict]:
        if columnName == "acc1km_percentage":
            bins = [0, 25, 50, 75, 100]
            labels = [r"0% - 25%", r"25% - 50%", r"50% - 75%", r"75% - 100%"]
            categoryData = df[columnName].clip(0, 100)
        elif columnName == "spatialConcentration":
            bins = [0, 0.2, 0.3, 0.4, 1]
            labels = [r"0% - 20%", r"20% - 30%", r"30% - 40%", r"40% - 100%"]
            categoryData = df[columnName].clip(0, 100)
        elif columnName == "spatialCoverage":
            bins = [0, 0.03, 0.06, 0.12, 1]
            labels = [r"0% - 3%", r"3% - 6%", r"6% - 12%", r"12% - 100%"]
            categoryData = df[columnName].clip(0, 1)
        elif "gini" in columnName:
            bins = [0, 0.25, 0.5, 0.75, 1]
            labels = [r"0.00 - 0.25", r"0.25 - 0.50", r"0.50 - 0.75", r"0.75 - 1.00"]
            categoryData = df[columnName].clip(0, 1)
        else:
            bins = [0, 0.25, 0.5, 0.75, 1]
            labels = [r"0% - 25%", r"25% - 50%", r"50% - 75%", r"75% - 100%"]
            categoryData = df[columnName].clip(0, 1)
            
        color = pd.cut(categoryData, bins=bins, labels=labels, include_lowest=True)
        colorMapping = dict(zip(labels, BAR_COLORS[0]))
        
        return color.map(colorMapping), colorMapping