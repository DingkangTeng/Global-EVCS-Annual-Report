import os
import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib.ticker import PercentFormatter
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from typing import Sequence

from __setting import EUR, CHN, ASEAN, GS, REGION_C
from __plot import plt
from .__text import _CITIES_STD_LEGEND, _ISO3, _LEGEND, _HEAT_STD_LEGEND

class globalPlot:
    __slots__ = ["language", "savePath"]

    def __init__(self, language: str, savePath: str) -> None:
        self.language = language
        self.savePath = savePath

        return

    # Hbar for global condition
    def hbar(self, df: pd.DataFrame, cols: Sequence[str]) -> None:
        # Regroup
        conditions = [
            df.index.isin(CHN),
            df.index.isin(EUR),
            df.index.isin(ASEAN),
            df.index == "USA",
            df.index.isin({"JPN", "KOR", "CAN", "AUS", "NZL"}),
            df.index.isin(GS)
        ]
        choices = ["CHN_ALL", "EUR", "ASEAN", "USA", "Other_Dev", "GS"]
        df["region"] = np.select(conditions, choices, default="Other")

        # Add region based color
        regionColors = REGION_C
        df["colors"] = df["region"].map(regionColors)
        legendHandles: list[Patch | Line2D] = [
            Patch(
                color=color,
                label=_ISO3[region][self.language]
            ) for region, color in regionColors.items()
        ]
        legendHandles.append(
            Line2D([0], [0], color="gray", linestyle='--', linewidth=3, label=_LEGEND["mean"][self.language])
        )

        # Plot
        ## Rename country
        df = self.__renameISO(df)
        barPlot = plt.subplot("BIG", 2, 5, legend=False, constrained=False) # 添加4个gini后就是14个子图了

        for i, col in enumerate(cols):
            single = plt.subplot("SLIM", 1, 2, widthRatios=[5, 3], legend=False)
            barSingle = single.fig
            barAx = single.axs[0]
            ax = barPlot.axs[i]
            subdf = df[[col, "colors"]].dropna().sort_values(by=col)
            subdf[col].plot.barh(
                ax=ax,
                color=subdf["colors"].tolist(),
                legend=False
            )
            subdf[col].plot.barh(
                ax=barAx,
                color=subdf["colors"].tolist(),
                legend=False
            )

            meanVal = subdf[col].mean()

            if "gini" not in col:
                ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0, symbol=''))
                barAx.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0, symbol=''))
                meanText = f"{meanVal * 100:.0f}%"
            else:
                meanText = f"{meanVal:.2f}"

            # Add mean
            ax.axvline(x=meanVal, color="gray", linestyle="--", linewidth=3)
            barAx.axvline(x=meanVal, color="gray", linestyle="--", linewidth=3)             
            ax.text(
                meanVal, 1.02,
                meanText,
                transform=ax.get_xaxis_transform(),
                ha="center", va="bottom",
                fontfamily="Times New Roman"
            )
            barAx.text(
                meanVal, 1.02,
                meanText,
                transform=barAx.get_xaxis_transform(),
                ha="center", va="bottom",
                fontfamily="Times New Roman"
            )

            ax.set_xlabel(_CITIES_STD_LEGEND[col][self.language])
            barAx.set_xlabel(_CITIES_STD_LEGEND[col][self.language])
            ax.set_ylabel(_LEGEND["country"][self.language]) if i == 0 or i == 5 else ax.set_ylabel("")
            barAx.set_ylabel(_LEGEND["country"][self.language])

            legendAx = single.axs[1]
            legendAx.axis("off")
            for spine in ["top", "right", "bottom", "left"]:
                legendAx.spines[spine].set_visible(False)
            legendAx.legend(
                loc="lower right",
                handles=legendHandles,
                ncols=1
            )

            plotPath = os.path.join(self.savePath, "Global")
            os.makedirs(plotPath, exist_ok=True)
            single.fig.patch.set_visible(False)
            plt.plot(
                plotPath,
                "golbal_median_{}.jpg".format(col),
                barSingle
            )

        barPlot.fig.legend(
            loc="lower center",
            handles=legendHandles,
            ncols=len(legendHandles)
        )

        barPlot.fig.subplots_adjust(wspace=0.6)
        barPlot.fig.patch.set_visible(False)
        barPlot.plot(
            os.path.join(self.savePath, "Global"), "golbal_median.jpg"
        )

        return
    
    # Heat map for Socioeconomic and Land-use Characteristics
    def heat(
        self,
        df: pd.DataFrame, cols: list,
        percentage: bool = True,
        lang: str = "zh"
    )-> None:
        df = df[cols].dropna().sort_index()
        df *= 100 if percentage else df # change to 100%

        # Saperate
        df = df[df.index.isin(CHN | ASEAN | {"JPN", "KOR"} | {"USA", "CAN"} | {"AUS", "NZL"} | GS | EUR)]
        # df1 = df[~df.index.isin(EUR)]
        # df2 = df[df.index.isin(EUR)]

        for sub, name in [(df, "all")]: #, (df1, "1"), (df2, "2")]:
            # Rename country
            sub = self.__sortByISO(sub)
            sub = self.__renameISO(sub, renameCol=True, heat=True)

            # Adjust cube
            r, c = sub.shape
            CELL_SIZE = 0.6
            figsize1 = (c * CELL_SIZE * 2.6 if lang == "zh" else c * CELL_SIZE * 3, r * CELL_SIZE)
            figsize2 = (c * CELL_SIZE * 4, r * CELL_SIZE)

            for i, figsize in enumerate([figsize1, figsize2]):
                _, ax = plt.figure(figsize)
                sns.heatmap(
                    sub,
                    ax=ax,
                    vmin=0,
                    vmax=100 if percentage else 1,
                    cmap="RdBu_r",
                    annot=True,
                    fmt=".0f" if percentage else ".2f",
                    annot_kws={
                        "family": "Times New Roman"
                    },
                    cbar_kws={
                        "shrink": 0.4,   # hight
                        "aspect": 30     # width(bigger slimer)
                    }
                )

                # Adjust ax
                ax.set_xticklabels(ax.get_xticklabels(), rotation=90 if i==1 else 90)
                ax.set_xlabel(_HEAT_STD_LEGEND["xlabel_acc" if percentage else "xlabel_gini"][self.language])
                ax.set_ylabel(_LEGEND["country"][self.language])
                
                plt.plot(
                    os.path.join(self.savePath, "Global"),
                    f"golbal_heat_{cols}_{name}_{i+1}.jpg",
                    bbox_inches="tight"
                )

        return
    
    # Rename country
    def __renameISO(self, df: pd.DataFrame, renameCol: bool = False, heat: bool = False) -> pd.DataFrame:
        if renameCol:
            return df.rename(
                index={
                    code: info[self.language] for code, info in _ISO3.items()
                },
                columns={
                    col: _HEAT_STD_LEGEND[col][self.language] if heat else
                        _CITIES_STD_LEGEND[col][self.language] for col in df.columns
                }
            )
        
        else:
            return df.rename(
                index={
                    code: info[self.language] for code, info in _ISO3.items()
                }
            )
        
    @staticmethod
    def __sortByISO(df: pd.DataFrame) -> pd.DataFrame:
        group_map = {}
        for order, group in enumerate([CHN, ASEAN, {"JPN", "KOR"}, {"USA", "CAN"}, {"AUS", "NZL"}, GS, EUR]):
            for code in group:
                group_map[code] = order

        df["_group"] = df.index.to_series().map(group_map.get)
        df = df.sort_values(by=["_group", df.columns[0]], ascending=[True, False])
        
        return df.drop(["_group"], axis=1)