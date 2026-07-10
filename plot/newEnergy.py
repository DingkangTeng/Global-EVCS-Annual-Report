import os
import numpy as np
import rasterio as rio
import geopandas as gpd
from rasterio.mask import mask
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform, reproject, Resampling, array_bounds
from rasterio.io import MemoryFile
from typing import Union, Self

from analysis import analysisByCities
from __setting import EUR, CHN, ASEAN, getUtmZone, CHN_ALBERS, ASIA_N_LAMBERT, IBGE_ALBERS
from __plot import plt, LABEL_SIZE
from .__template import mapTemplate, languageTemplate
from .__text import _ISO3

class newEnergy(mapTemplate, languageTemplate):
    __slots__ = (
        "dataRoot", "savePath",
        "level1", "level2", "dashline"
    )

    def __init__(
        self,
        data: analysisByCities, mapElement: str, savePath: str,
        language: languageTemplate.LANGUAGE = "zh"
    ) -> None:
        languageTemplate.__init__(self, language)

        self.dataRoot = data.savePath
        self.savePath = os.path.join(savePath, "fig_{}".format(language))
        os.makedirs(self.savePath, exist_ok=True)

        self.level1 = gpd.read_file(data.boundary, layer="level1", encoding="utf-8")
        self.level2 = gpd.read_file(data.boundary, layer="level2", encoding="utf-8")
        self.dashline = (
            gpd.read_file(mapElement, layer="JDX", encoding="utf-8").geometry.to_crs(CHN_ALBERS),
            gpd.read_file(mapElement, layer="JDX_sansha", encoding="utf-8").geometry.to_crs(CHN_ALBERS)
        )

        return
    
    def draw(self, iso3: Union[str, list[str], set[str]] = "Global") -> Self:
        # Define projection
        level2AK = gpd.GeoSeries()
        level2HW = gpd.GeoSeries()
        level1MEX = gpd.GeoSeries()
        level2MEX = gpd.GeoSeries()
        level1BRA = gpd.GeoSeries()
        level2BRA = gpd.GeoSeries()
        level1MEX = gpd.GeoSeries()
        level2MEX = gpd.GeoSeries()
        if isinstance(iso3, list) or isinstance(iso3, set):
            level1 = self.level1[self.level1["iso3_code"].isin(iso3)].geometry
            level2 = self.level2[self.level2["iso3_code"].isin(iso3)].geometry
            crs = 4326, None, None

        elif iso3 == "Global":
            crs = 3857, None, None
            level1 = self.level1.geometry.to_crs(3857)
            level2 = self.level2.geometry.to_crs(3857)
            
        elif iso3 in {"EUR", "ASEAN", "JPN&KOR", "AUS&NZL"}:
            crs = (
                3035 if iso3 == "EUR" else # ETRS89-LAEA
                27703 if iso3 == "ASEAN" else # WGS 84 / Equi7 Asia
                ASIA_N_LAMBERT if iso3 == "JPN&KOR" else # Asia North Lambert Conformal Conic
                3577 # GDA94 / Australian Albers
            ), None, None
            region = (
                EUR if iso3 == "EUR" else
                ASEAN if iso3 == "ASEAN" else
                {"JPN", "KOR"} if iso3 == "JPN&KOR" else
                {"AUS", "NZL"}
            )
            level1 = self.level1[self.level1["iso3_code"].isin(region)].geometry.to_crs(crs[0])
            level2 = self.level2[self.level2["iso3_code"].isin(region)].geometry.to_crs(crs[0])

        # Special case for CHN
        elif iso3 == "CHN":
            crs = CHN_ALBERS, None, None
            level1 = self.level1[self.level1["iso3_code"].isin(CHN)].geometry.to_crs(CHN_ALBERS)
            level2 = self.level2[self.level2["iso3_code"].isin(CHN)].geometry.to_crs(CHN_ALBERS)

        # Special case for Global South
        elif iso3 == "GS":
            crs = 2048, IBGE_ALBERS, 6372
            # BRA
            level1BRA = self.level1[self.level1["iso3_code"] == "BRA"].geometry.to_crs(IBGE_ALBERS) # SIRGAS 2000 / Brazil Albers
            level2BRA = self.level2[self.level2["iso3_code"] == "BRA"].geometry.to_crs(IBGE_ALBERS)
            # MEX
            level1MEX = self.level1[self.level1["iso3_code"] == "MEX"].geometry.to_crs(6372) # Mexico ITRF2008 / LCC
            level2MEX = self.level2[self.level2["iso3_code"] == "MEX"].geometry.to_crs(6372)
            # ZAF
            level1 = self.level1[self.level1["iso3_code"] == "ZAF"].geometry.to_crs(2048) # Hartebeesthoek94 / Lo19
            level2 = self.level2[self.level2["iso3_code"] == "ZAF"].geometry.to_crs(2048)
        
         # Special case for USA and USA&CAN
        elif iso3 == "USA&CAN" or iso3 == "USA":
            crs = 5070, 6393, 26904
            # AK
            level2AK = self.level2[self.level2["level2"] == "Alaska"].geometry.to_crs(6393)
            # HW
            level2HW = self.level2[self.level2["level2"] == "Hawaii"].geometry.to_crs(26904)
            # NORMAL
            level1 = self.level1[
                self.level1["iso3_code"].isin({"USA", "CAN"}) if iso3 == "USA&CAN" else self.level1["iso3_code"] == "USA"
            ].geometry.to_crs(5070)
            level2 = self.level2[
                self.level2["iso3_code"].isin({"USA", "CAN"}) if iso3 == "USA&CAN" else self.level2["iso3_code"] == "USA"
            ].geometry.to_crs(5070)

        else:
            level1 = self.level1[self.level1["iso3_code"].isin(CHN)]
            crs = getUtmZone(level1), None, None
            level1 = level1.geometry.to_crs(crs[0])
            level2 = self.level2[self.level2["iso3_code"] == iso3].geometry.to_crs(crs[0])

        for tifName, name, v in [
            ("wind_speed_cog_10m.tif", "wind", (0, 20)), # Color bar range
            (os.path.join("GHI", "GHI.tif"), "solar", (0, 8)),
        ]:
            tif = os.path.join(self.dataRoot, tifName)
            # Draw
            fig, ax = plt.figure("W")

            ## Special fig for USA
            if iso3 == "USA" or iso3 == "USA&CAN":
                axAK = fig.add_axes((0.15 if iso3 == "USA" else 0.07, 0.02, 0.15, 0.15))
                axHA = fig.add_axes((0.28 if iso3 == "USA" else 0.20, 0.02, 0.15, 0.15)) 
                # Alaska
                assert crs[1] is not None, "CRS for Alaska must be defined."
                self._plotMap(
                    self.__cutRaster(tif, crs[1], level2AK), None,
                    level1.to_crs(crs[1]), level2AK,
                    None,
                    "AK", axAK,
                    frame=True,
                    note={
                        "x": 0.05, "y": 0.95,
                        "text": "Alaska",
                        "ha": "left", "va": "top"
                    },
                    v=v
                )
                # Hawaii
                self._plotMap(
                    self.__cutRaster(tif, crs[2], level2HW), None,
                    level1.to_crs(crs[2]), level2.to_crs(26904),
                    None,
                    "HA", axHA,
                    frame=True,
                    note={
                        "x": 0.05, "y": 0.05,
                        "text": "Hawaii",
                        "ha": "left", "va": "bottom"
                    },
                    v=v
                )
                df = self.__cutRaster(tif, crs[0], level1)

            ## Special figure for CHN
            elif iso3 == "CHN":
                df = self.__cutRaster(tif, crs[0], level1)
                axJDX = fig.add_axes((0.22, 0.02, 0.25, 0.25))
                self._plotMap(
                    df, None,
                    self.dashline[0], self.dashline[1],
                    None,
                    "JDX", axJDX,
                    otherLayer=[level2.boundary],
                    frame=True,
                    v=v
                )

            # Special figure for Global South
            elif iso3 == "GS":
                axBRA = fig.add_axes((-0.6, 0, 1, 1))
                self._plotMap(
                    self.__cutRaster(tif, crs[1], level1BRA), None,
                    level1BRA, level2BRA,
                    None,
                    "BRA", axBRA,
                    frame=True,
                    note={
                        "x": 0.05, "y": 0.95,
                        "text": _ISO3["BRA"][self.language],
                        "ha": "left", "va": "top",
                        "fontsize": LABEL_SIZE
                    },
                    v=v
                )
                axMEX = fig.add_axes((-1.3, 0, 1, 1))
                self._plotMap(
                    self.__cutRaster(tif, crs[2], level1MEX), None,
                    level1MEX, level2MEX,
                    None,
                    "MEX", axMEX,
                    frame=True,
                    note={
                        "x": 0.90, "y": 0.95,
                        "text": _ISO3["MEX"][self.language],
                        "ha": "left", "va": "top",
                        "fontsize": LABEL_SIZE
                    },
                    v=v
                )
                df = self.__cutRaster(tif, crs[0], level1)
            
            else:
                df = self.__cutRaster(tif, crs[0], level1)

            # Main map
            cbarFig, cbarAx = plt.figure("HorBar")
            self._plotMap(
                df, None,
                level1, level2,
                None,
                iso3, ax,
                getCbar=cbarAx,
                v=v
            )

            # Save
            savePath = os.path.join(self.savePath, str(iso3))
            os.makedirs(savePath, exist_ok=True)
            plt.plot(
                savePath,
                "map_{}_raw.jpg".format(name),
                fig=fig, bbox_inches="tight"
            )
            plt.plot(
                savePath,
                "map_{}_cbar.jpg".format(name),
                fig=cbarFig, bbox_inches="tight"
            )

        return self
    
    @staticmethod
    def __cutRaster(
        tif: str, crs: Union[str, int, None], boundary: gpd.GeoSeries,
    ) -> tuple[np.ndarray, Affine]:
        if crs is None:
            raise ValueError("CRS must be specified for raster reprojection.")
        
        with rio.open(tif, options=["NUM_THREADS=ALL_CPUS"]) as src:
            inputCRS = src.crs.to_epsg()

            if boundary.crs is not None and boundary.crs.to_epsg() != inputCRS:
                boundary = boundary.to_crs(src.crs)
            elif boundary.crs is None:
                raise ValueError("Boundary GeoSeries must have a valid CRS.")
            
            outImage, outTransform = mask(src, [boundary.union_all()], crop=True)

            if inputCRS == crs:
                return outImage[0], outTransform
            
            srcKwargs = src.meta.copy()
            srcKwargs.update({
                "height": outImage.shape[1],
                "width": outImage.shape[2],
                "transform": outTransform,
                "crs": src.crs
            })

            dstTransform, dstWidth, dstHeight = calculate_default_transform(
                src.crs, crs, outImage.shape[2], outImage.shape[1],
                *array_bounds(outImage.shape[1], outImage.shape[2], outTransform),
                resolution=1000
            )

            dstKwargs = src.meta.copy()
            dstKwargs.update({
                "crs": crs,
                "transform": dstTransform,
                "width": dstWidth,
                "height": dstHeight
            })

            memfile = MemoryFile()
            with memfile.open(**dstKwargs) as dst:
                reproject(
                    source=outImage[0],
                    destination=rio.band(dst, 1),
                    src_transform=outTransform,
                    src_crs=src.crs,
                    dst_transform=dstTransform,
                    dst_crs=crs,
                    resampling=Resampling.average,
                    src_nodata=src.nodata,
                    dst_nodata=src.nodata,
                    num_threads=0
                )
            with memfile.open() as finalDs:
                projected = finalDs.read(1)
            memfile.close()

            return projected, dstTransform