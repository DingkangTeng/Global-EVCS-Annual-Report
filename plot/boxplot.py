import os
import numpy as np

from __setting import EUR, CHN
from __plot import plt
from analysis import analysisByCities
from .__template import baseTemplate
from .__text import _BOXPLOT_STD_LEGEND, _LEGEND

class plotBox(baseTemplate):
    __slots__ = ["data", "savePath"]

    __iso3s = ["CHN", "USA", "EUR", "Global"]

    def __init__(self, data: analysisByCities, savePath: str, language: baseTemplate.LANGUAGE = "zh") -> None:
        baseTemplate.__init__(self, language)

        self.data = data
        self.savePath = savePath

        return

    def drawAll(self, cols: list[str] = [], iso3s: list[str] = __iso3s, maxThread: int = 1) -> None:
        cols = list(self.sp) if cols == [] else cols
        
        for columnName in cols:
            if columnName not in self.cols:
                raise ValueError(f"'{columnName}' do not exists. Please use: {self.cols}")
        
        cols = [item for col in cols for item in (col, col + "_BuiltUp", col + "_Other")]

        df = self.data.df[["iso3_code"] + cols]

        # Initial data
        ## For multi countries in one map
        for iso3 in iso3s:
            savePath = os.path.join(self.savePath, iso3)

            if iso3 == "Global":
                df2 = df.drop(columns="iso3_code").dropna()
            elif iso3 == "EUR":
                df2 = df[df["iso3_code"].isin(EUR)].drop(columns="iso3_code").dropna()
            elif iso3 == "CHN":
                df2 = df[df["iso3_code"].isin(CHN)].drop(columns="iso3_code").dropna()
            else:
                df2 = df[df["iso3_code"] == iso3].drop(columns="iso3_code").dropna()

            if df2.shape[0] == 0:
                raise RuntimeError(f"No data for {iso3s}")
            
            # Boxplot
            nGroups = len(cols) // 3
            multi = plt.subplot("W", 1, nGroups)
            axs = multi.axs

            for i in range(nGroups):
                ax = axs[i]
                groupCols = cols[i*3:(i+1)*3]
                subdf = df2[groupCols]
                subdf.replace(-100, np.nan, inplace=True)
                # Change to percentage
                if "gini" not in groupCols[0]:
                    subdf *= 100

                subdf.boxplot(ax=ax)

                ax.set_xticklabels([_LEGEND[c][self.language] for c in ["all", "built", "nonbuilt"]])
                ax.set_ylabel(_BOXPLOT_STD_LEGEND[groupCols[0]][self.language])

            plt.plot(savePath, "boxplot.jpg", bbox_inches="tight")

        return
