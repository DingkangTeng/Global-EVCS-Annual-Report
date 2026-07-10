import os
import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde, binned_statistic
import matplotlib.ticker as ticker
import matplotlib.lines as mlines
from matplotlib.ticker import PercentFormatter
from tqdm import tqdm
from typing import overload

from __plot import plt, BAR_COLORS
from __setting import EUR
from .__template import languageTemplate
from .__text import _ISO3, _LEGEND

MAX_PLOT_POINTS = 5000

class plotAccessibilityCurve(languageTemplate):
    __slots__ = ["dataPath", "savePath", "threshold"]

    def __init__(
        self,
        dataPath: str,
        savePath: str,
        threshold: int = 29, language: languageTemplate.LANGUAGE = "zh"
    ) -> None:
        languageTemplate.__init__(self, language)

        self.dataPath = os.path.join(dataPath, "accessibility")
        self.savePath = savePath
        self.threshold = threshold
        
        return

    def plotByCountry(self, iso3s: list[str]) -> None:
        bar = tqdm(total=len(iso3s)*2+1, desc="Drawing Cumulative Curve for accessibility", unit="country")

        _, ax = plt.figure(figsize="D")
        ax2 = ax.twinx() # Distriubtion

        allData = []
        for iso3 in iso3s:
            bar.set_postfix(iso3=iso3)
            if iso3 == "EUR":
                df = pd.concat([
                    pd.read_csv(
                        os.path.join(self.dataPath, c, "{}.csv".format(c))
                    ) for c in sorted(EUR)
                ])
            else:
                df = pd.read_csv(
                    os.path.join(self.dataPath, iso3, "{}.csv".format(iso3))
                )

            allData.append(df)
            bar.update()
        
        bar.set_postfix(iso3="All data curve")
        agrs = self.__cumulativeCurve(pd.concat(allData), "All Data", 0, (ax2, ax))
        bar.update()

        # Draw by countries
        i = 1
        for df in allData:
            self.__cumulativeCurve(df, iso3s[i-1], i-1, (ax2, ax), agrs)
            i += 1
            bar.update()
        
        self.__adjustAx((ax2, ax), *agrs)
        lines, labels = ax.get_legend_handles_labels()
        cumLine = mlines.Line2D([], [], color="gray", linestyle="--", label=_LEGEND["acc"][self.language])
        ax2.legend(
            lines + [cumLine],
            labels + [_LEGEND["acc"][self.language]],
            loc="lower right",
            bbox_to_anchor=(1, 0.05)
        )

        plt.plot(os.path.join(self.savePath, "Global"), "{}_accessibility_cumulative_curve.jpg".format(iso3s))
        bar.close()

        return

    def plotAll(self, color: int = 2) -> None:
        countries = os.listdir(self.dataPath)
        bar = tqdm(total=len(countries)+2, desc="Drawing Cumulative Curve for accessibility", unit="country")

        euData = []
        globalData = []
        for iso3 in countries:
            bar.set_postfix(iso3=iso3)
            df = pd.read_csv(
                os.path.join(self.dataPath, iso3, "{}.csv".format(iso3))
            )
            self.__cumulativeCurve(df, iso3, color)
            if iso3 in EUR: euData.append(df)
            elif iso3 in {"CHN", "USA"}: globalData.append(df)
            bar.update()

        # Process EUR data
        EURDf = pd.concat(euData)
        bar.set_postfix(iso3="EUR")
        self.__cumulativeCurve(EURDf, "EUR", color)
        bar.update()

        # Process CHN\USA\ERU
        bar.set_postfix(iso=r"CHN\USA\EUR")
        self.__cumulativeCurve(
            pd.concat(globalData + [EURDf]),
            "Global",
            color
        )
    
        return

    @overload
    def __cumulativeCurve(
        self,
        result: pd.DataFrame, iso3: str,
        color: int, inputAx: tuple[plt.Axes, plt.Axes], agrs: tuple | None = None
    ) -> tuple[float, float, np.bool, float]:
        ...

    @overload
    def __cumulativeCurve(
        self,
        result: pd.DataFrame, iso3: str,
        color: int, inputAx: None = None, agrs: tuple | None = None
    ) -> None:
        ...

    def __cumulativeCurve(
        self,
        result: pd.DataFrame, iso3: str,
        color: int, inputAx: tuple[plt.Axes, plt.Axes] | None = None, agrs: tuple | None = None
    ) -> tuple[float, float, np.bool, float] | None:
        savePath = os.path.join(self.savePath, iso3)
        if not os.path.exists(savePath): os.makedirs(savePath)

        df = result.sort_values("accessibility")
        df["accessibility"] /= 1000
        
        # Merge data over 30 km
        maskOverThres = df["accessibility"] > self.threshold
        if agrs is None:
            overThres = maskOverThres.any()
            lastX = self.threshold + 1
            xmin = df["accessibility"].min()
            xmax = lastX if overThres else df["accessibility"].max()
        else:
            xmin, xmax, overThres, lastX = agrs

        if iso3 == "All Data":
            return xmin, xmax, overThres, lastX
        
        if overThres:
            pop = df.loc[maskOverThres, "population"].sum()
            df = df[~maskOverThres].reset_index(drop=True)
            df.loc[df.shape[0]] = [lastX, pop]

        # Calculating cumulative sum
        df["cumulative_pop"] = df["population"].cumsum()
        df["cumulative_percent"] = df["cumulative_pop"] / df["population"].sum()

        # Sample
        n = df.shape[0]
        dfPlot = df if n < MAX_PLOT_POINTS else df.iloc[np.linspace(0, n-1, MAX_PLOT_POINTS, dtype=int)]
        
        if inputAx is None:
            _, ax2 = plt.figure(figsize="D")
            ax = ax2.twinx()
        else:
            ax, ax2 = inputAx
        
        # Draw cumulative percentage
        ax.plot(
            dfPlot["accessibility"], dfPlot["cumulative_percent"], 
            color=BAR_COLORS[1][color],
            linewidth=2,
            linestyle="--",
            label=_ISO3[iso3].get(self.language, iso3)
        )
        ax.set_ylabel(_LEGEND["accy"][self.language])
        
        # Draw distribution
        maskFit = df["accessibility"] <= xmax
        xFit = df.loc[maskFit, "accessibility"].values
        wFit = df.loc[maskFit, "population"].values
        ## Group data
        bin_width = 0.1
        bins = np.arange(0, xmax + bin_width, bin_width)
        binCenters = (bins[:-1] + bins[1:]) / 2
        binPop, _, _ = binned_statistic(xFit, wFit, statistic='sum', bins=bins) # type: ignore
        nonZero = binPop > 0
        xFit = binCenters[nonZero]
        wFit = binPop[nonZero]
        kde = gaussian_kde(xFit, weights=wFit)
        xDense = np.linspace(0, xmax, 200)
        ax2.plot(
            xDense, kde(xDense),
            color=BAR_COLORS[1][color],
            linewidth=1.5,
            label=_ISO3[iso3].get(self.language, iso3)
        )
        ax2.set_xlabel(_LEGEND["accx"][self.language])
        ax2.set_ylabel(f"{_LEGEND["popPercentage"][self.language]}{_LEGEND["%"][self.language]}")

        if inputAx is None:
            self.__adjustAx((ax, ax2), xmin, xmax, overThres, lastX)
            plt.plot(savePath, "{}_accessibility_cumulative_curve.jpg".format(iso3))
            return
        
        else:
            return xmin, xmax, overThres, lastX
    
    @staticmethod
    def __adjustAx(axs: tuple[plt.Axes, plt.Axes], xmin: float, xmax: float, overThres: np.bool, lastX: float) -> None:
        ax, ax2 = axs
        # Modify x label
        ## Get the range of axes, and add 5% margin
        margin = 0.05 * (xmax - xmin)
        left = xmin - margin
        right = xmax + margin
        ax.set_xlim(left, right)
        ## Using MaxNLocator to choose integer label
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True, steps=[1, 2, 5, 10]))

        ## Ensure that the merge point lastX is also used as a scale and covers the label
        xticks = ax.get_xticks()
        xticks = [t for t in xticks if 0 <= t <= right]
        if overThres:
            if lastX not in xticks:
                xticks = np.append(xticks, lastX)
            labels = [f"{int(x)}" if x != lastX else f"{int(lastX)}+" for x in xticks]
            ax.set_xticks(xticks, labels=labels)
        else:
            ax.set_xticks(xticks, labels=[f"{int(x)}" for x in xticks])

        # Adjust y
        ax.set_ylim(ymin=-0.03, ymax=1.03)
        ax.set_yticks(np.linspace(0, 1, 6))
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
        ymax2 = ax2.get_ylim()[1]
        ax2.set_ylim(ymin=-0.03 * ymax2, ymax=ymax2 * 1.03)
        ax2.set_yticks(np.linspace(0, ymax2, 6))
        ax2.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))

        return