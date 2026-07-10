import os
import matplotlib.ticker as mtick
from typing import Self

from __setting import EUR, CHN
from __plot import plt, BAR_COLORS
from analysis import analysisByCities
from .__template import baseTemplate
from .__text import _SCATTER_STD_LEGEND

class plotScatter(baseTemplate):
    __slots__ = ["data", "savePath"]

    __COLS_STD_NAME = {
        "spatialConcentration": "spatial_concentration_builtup",
        "spatialCoverage": "spatial_coverage_evcs_builtup",
        "spatialCoverageForPOI1": "spatial_coverage_public_facility_builtup",
        "spatialCoverageForPOI2": "spatial_coverage_commercial_facility_builtup",
        "spatialCoverageForPOI3": "spatial_coverage_leasure_facility_builtup",
        "spatialCoverageForPop": "spatial_coverage_population_builtup"
    }

    def __init__(self, data: analysisByCities, savePath: str, language: baseTemplate.LANGUAGE = "zh") -> None:
        baseTemplate.__init__(self, language)

        self.data = data
        self.savePath = savePath

        return

    def draw(self, columnName: str, iso3: str | list[str] | set[str] = "Global") -> Self:
        if columnName not in self.cols:
            raise ValueError(f"'{columnName}' do not exists. Please use: {self.cols}")
        
        builtUpCol = columnName + "_BuiltUp"
        nonBuiltCol = columnName + "_Other"
        df = self.data.df[["iso3_code", builtUpCol, nonBuiltCol]].dropna()

        # Initial data
        ## For multi countries in one map
        if isinstance(iso3, list) or isinstance(iso3, set):
            savePath = os.path.join(self.savePath, "_".join(iso3))
            df = df[df["iso3_code"].isin(iso3)].drop(columns="iso3_code")
            
        elif iso3 == "Global":
            savePath = os.path.join(self.savePath, "Global")

        elif iso3 == "EUR":
            savePath = os.path.join(self.savePath, "EUR")
            df = df[df["iso3_code"].isin(EUR)].drop(columns="iso3_code")

        # Special case for CHN
        elif iso3 == "CHN":
            savePath = os.path.join(self.savePath, "CHN")
            df = df[df["iso3_code"].isin(CHN)].drop(columns="iso3_code")

        else:
            savePath = os.path.join(self.savePath, iso3)
            df = df[df["iso3_code"] == iso3].drop(columns="iso3_code")

        if df.shape[0] == 0:
            raise RuntimeError(f"No data for {iso3}")
        
        # Scatter
        _, ax = plt.figure("D")
        df.plot.scatter(
            x=builtUpCol,
            y=nonBuiltCol,
            ax=ax,
            color=BAR_COLORS[1][0],
        )

        # Add y=x line
        ax.axline((0, 0), slope=1, color="red", linestyle="--", label="y=x")

        # Change axis ticker labels to percentage format
        if columnName == "acc1km_percentage":
            ax.set_xlim(xmin=-5, xmax=105)
            ax.xaxis.set_major_formatter(mtick.PercentFormatter(100))
            ax.set_ylim(ymin=-5, ymax=105)
            ax.yaxis.set_major_formatter(mtick.PercentFormatter(100))
        else:
            ax.set_xlim(xmin=-0.05, xmax=1.05)
            ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
            ax.set_ylim(ymin=-0.05, ymax=1.05)
            ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

        ax.set_xlabel(_SCATTER_STD_LEGEND[builtUpCol][self.language])
        ax.set_ylabel(_SCATTER_STD_LEGEND[nonBuiltCol][self.language])
        ax.legend()

        plt.plot(savePath, "{}.jpg".format(self.__COLS_STD_NAME[columnName]), bbox_inches="tight")
        
        return self
