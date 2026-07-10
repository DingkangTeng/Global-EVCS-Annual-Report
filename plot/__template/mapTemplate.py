import geopandas as gpd
import numpy as np
import seaborn as sns
from rasterio.transform import Affine
from rasterio.plot import show as rshow
from matplotlib_scalebar.scalebar import ScaleBar
# import matplotlib.patheffects as patheffects
from matplotlib.lines import Line2D
# from adjustText import adjust_text
# from shapely.geometry import Point
from matplotlib.patches import Patch
from matplotlib.ticker import LinearLocator, PercentFormatter
from matplotlib.colorbar import Colorbar
from typing import Union

from __plot import plt, NOTE_SIZE, BAR_COLORS, BAR_COLORS_TRANS
from ..__text import _CITIES_STD_LEGEND, _LEGEND

# NoteDict
from typing import TypedDict, Required
class __NoteDict(TypedDict, total=False):
    x: Required[float]
    y: Required[float]
    text: Required[str]
    ha: Required[str]
    va: Required[str]
    fontsize: int

class mapTemplate:
    __slots__ = ()

    @staticmethod
    def _plotMap(
        df: Union[gpd.GeoDataFrame, gpd.GeoSeries, tuple[np.ndarray, Affine]],
        dfInvalid: Union[gpd.GeoDataFrame, gpd.GeoSeries, None], # Invalid data (EVCS<=10) is useless at present
        level1: gpd.GeoSeries, level2: gpd.GeoSeries,
        mainCities: Union[gpd.GeoDataFrame, None], # Main cities is useless at present
        iso3: Union[str, list[str], set[str]], ax: plt.Axes,
        otherLayer: list[Union[gpd.GeoDataFrame, gpd.GeoSeries]] | None = None,
        frame: bool = False, note: Union[__NoteDict, None] = None, # Remove text note at present
        getCbar: plt.Axes | None = None, v: tuple[float, float] = (0, 1)
    ) -> None:
        # Plot raster data
        if isinstance(df, tuple) and len(df) == 2:
            array, transform = df
            rshow(
                array,
                cmap="Spectral_r",
                vmin=v[0],
                vmax=v[1],
                transform=transform,
                ax=ax,
                adjust=False
            )
            if isinstance(getCbar, plt.Axes):
                ax.figure.colorbar(ax.images[-1], cax=getCbar, orientation="horizontal")
                getCbar.grid(False)

        elif isinstance(df, tuple) and len(df) != 2:
            raise ValueError("Invalid df format. Expected a tuple of (data, transform).")

        # Plot country boundary
        level1.plot(
            ax=ax,
            facecolor="whitesmoke" if not isinstance(df, tuple) else "none",
            # hatch="//",
            edgecolor="black",
            linewidth=0.8
        )

        # Plot vector data
        if not isinstance(df, tuple) and df.shape[0] > 0:
            df.plot(
                ax = ax,
                color=df["color"] if isinstance(df, gpd.GeoDataFrame) else "black",
                edgecolor="white",
                linewidth=0.5
            )

        # # Plot invalid data
        # if dfInvalid.shape[0] > 0:
        #     dfInvalid.plot(
        #         ax = ax,
        #         facecolor="none",
        #         edgecolor="gray",
        #         hatch="///",
        #         linewidth=0.5
        #     )

        # Plot province boundary
        if level2.shape[0] > 0:
            level2.boundary.plot(ax=ax, edgecolor="black", linewidth=0.8)

        # # Plot main cities
        # if iso3 != "Global" and mainCities is not None and mainCities.shape[0] > 0:
        #     mainCities.plot(
        #         ax=ax,
        #         markersize=25, color="white", edgecolor="black",
        #         linewidth=1,
        #         zorder=10
        #     )
        #     texts = []
        #     for row in mainCities.itertuples():
        #         point: Point = getattr(row, "geometry")
        #         name = getattr(row, "level3")
        #         x = point.x
        #         y = point.y
        #         texts.append(
        #             ax.text(
        #                 x, y+2000,
        #                 name,
        #                 fontsize=NOTE_SIZE*0.8,
        #                 fontfamily="Times New Roman",
        #                 ha="center", va="bottom",
        #                 path_effects=[
        #                     patheffects.Stroke(linewidth=2, foreground='white'),
        #                     patheffects.Normal()
        #                 ],
        #                 zorder=11
        #             )
        #         )
            
        #     # Adjust text space to avoid override
        #     if iso3 != "AK" and iso3 != "HA" and iso3 != "USA":
        #         adjust_text(
        #             texts,
        #             ax=ax,
        #             autoalign="xy",
        #             expand_points=(5000, 5000),
        #             expand_text=(5000, 5000),
        #             force_points=(0.8, 0.8),
        #             arrowprops=dict(arrowstyle='-', color='gray', lw=0.5)
        #         )

        # Scale bar for formating
        if iso3 != "AK" and iso3 != "HA" and iso3 != "JDX":
            mapTemplate._scaleBar(ax)

        if otherLayer is not None:
            for layer in otherLayer:
                layer.plot(ax=ax, edgecolor="black", linewidth=0.8)

        # # Note
        # if note is not None:
        #     ax.text(
        #         note["x"], note["y"], note["text"],
        #         transform=ax.transAxes,
        #         ha=note["ha"], va=note["va"],
        #         fontsize=note.get("fontsize", NOTE_SIZE), weight="bold",
        #     )

        # Beauty
        ax.grid(False)
        if frame:
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_linewidth(1)
        else:
            ax.set_axis_off()
            ax.set_frame_on(False)

        # Adjust map range
        if iso3 == "Global":
            ax.set_ylim(-7600000, 12000000)
        elif iso3 == "EUR":
            ax.set_xlim(2600000, 6550000)
            ax.set_ylim(1350000, 5450000)
        elif iso3 == "USA":
            ax.set_xlim(-2400000, 2400000)
            ax.set_ylim(100000, 3240000)
        elif iso3 == "USA&CAN":
            ax.set_xlim(-2400000, 3200000)
            ax.set_ylim(100000, 4000000)
        elif iso3 == "JPN&KOR":
            ax.set_xlim(2440000, 3610000)
        elif iso3 == "CHN":
            ax.set_xlim(-2867426, 2448970)
            ax.set_ylim(1674761, 6123711)
        ## Special case
        elif iso3 == "HA": # Hawaii
            ax.set_xlim(320000, 950000)
            ax.set_ylim(2080000, 2470000)
        elif iso3 == "AK": # Alaska
            ax.set_xlim(-2400000, 1550000)
            ax.set_ylim(370000, 2420000)
        elif iso3 == "JDX": # JDX
            ax.set_xlim(100000, 1850000)
            ax.set_ylim(250000, 2600000)
        else:
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            print(
                f"No specific range for {iso3} was set. The automatically computed range is "
                f"x:({xmin:.0f}, {xmax:.0f}), y:({ymin:.0f}, {ymax:.0f})."
            )

        return
    
    @staticmethod
    def _plotHistogram(
        data: np.ndarray,
        ax: plt.Axes, columnName: str, iso3: str,
        language: str
    ) -> None:
        noPercent = columnName == "gini"

        sns.histplot(
            data,
            color=BAR_COLORS[1][0],
            edgecolor=BAR_COLORS_TRANS(0.8, 1)[0],
            ax=ax,
            bins=30,
            stat="probability"
        )

        # Statistic
        median = np.median(data)
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        percent = '' if noPercent else '%'
        ax.axvline(
            q1, color="green", linestyle='--', linewidth=1.5,
            label=f"{_LEGEND["Q1"][language]} = {q1:.2f}{percent}"
        )
        ax.axvline(
            median, color="red", linestyle='-', linewidth=2,
            label=f"{_LEGEND["median"][language]} = {median:.2f}{percent}"
        )
        ax.axvline(
            q3, color="green", linestyle='--', linewidth=1.5,
            label=f"{_LEGEND["Q3"][language]} = {q3:.2f}{percent}"
        )
        
        ax.set_ylabel(_LEGEND["cityPercentage"][language])
        xlabel = _CITIES_STD_LEGEND[columnName][language].replace("\n", "")
        ax.set_xlabel(xlabel)

        # CDF
        ax2 = ax.twinx()
        sortedData = np.sort(data)
        cumProb = np.arange(1, len(sortedData) + 1) / len(sortedData)
        ax2.plot(
            sortedData, cumProb,
            color=BAR_COLORS[1][2],
            linewidth=1.5,
            label=_LEGEND["cumPercentage"][language]
        )
        ax2.set_ylabel(f"{_LEGEND["cumPercentage"][language]}{_LEGEND["%"][language]}")
        ax2.set_ylim(0, 1)

        # Adjust y ticker
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
        ax2.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
        ax.yaxis.set_major_locator(LinearLocator(6))

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        # Sample n
        proxyArtist = Line2D([0], [0], linestyle="none", marker='', color="none")
        allLines = [proxyArtist] + lines1 + lines2
        allLabels = [f"{_LEGEND["n"][language]} = {data.shape[0]}"] + labels1 + labels2
        
        # Legend place choosen
        if (
            (columnName == "spatialCoverageForPOI1" and iso3 != "USA") or
            ((columnName == "spatialCoverageForPOI2" or columnName == "spatialCoverageForPOI3") and iso3 != "USA") or
            (columnName == "spatialCoverageForPop" and iso3 in {"EUR", "Global"}) or
            (columnName == "spatialCoverage") and iso3 == "AUS&NZL" or
            columnName == "gini"
        ):
            ax2.legend(
                allLines,
                allLabels,
                loc="upper left"
            )

        else:
            ax2.legend(
                allLines,
                allLabels,
                loc="upper right",
                bbox_to_anchor=(0.98, 0.95)
            )
        ax.legend().remove()
    
        return
    
    @staticmethod
    def _legend(
        iso3: str | list[str] | set[str],
        title: str,
        ax: plt.Axes, legend: list[Patch]
    ) -> None:
        ## Special case for USA/CHN to avoid legend override
        if iso3 in {"USA", "USA&CAN", "CHN"}:
            ax.legend(
                title=title,
                handles=legend,
                fontsize=NOTE_SIZE,
                loc="lower right",
                bbox_to_anchor=(
                    (1.15, 0) if iso3 in {"USA", "CHN"} else
                    (1, 0)
                ),
                ncol=1
            )
        elif iso3 == "EUR":
            ax.legend(
                title=title,
                handles=legend,
                title_fontsize=NOTE_SIZE,
                fontsize=NOTE_SIZE,
                loc="upper right",
                bbox_to_anchor=(1.05, 1),
                ncol=1
            )
        else:
            ax.legend(
                title=title,
                handles=legend,
                title_fontsize=NOTE_SIZE,
                fontsize=NOTE_SIZE,
                loc=(
                    "upper left" if iso3 == "JPN&KOR" else
                    "lower right" if iso3 == "GS" else
                    "best"
                ),
                ncol=1
            )
        
        return
    
    # Scale bar for formating
    @staticmethod
    def _scaleBar(ax: plt.Axes) -> None:
        scalebar = ScaleBar(
            dx=1, units="m",
            fixed_value=500, fixed_units="km",
            location="lower right",
            # Remove text
            scale_loc="none",
            label_loc="none"
        )
        ax.add_artist(scalebar)

        return