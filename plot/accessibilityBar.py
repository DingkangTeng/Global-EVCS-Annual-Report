import os
import pandas as pd
import numpy as np

from __setting import EUR, CHN, ASEAN, GS
from __plot import plt, TICK_SIZE
from .__template import languageTemplate
from .__text import _LEGEND, _ISO3

class plotAcccessibilityBar(languageTemplate):
    __slots__ = ["dataPath", "savePath", "threshold", "tickSizeMultiple"]

    __regions = ["CHN_ALL", "EUR", "GS", "ASEAN", "JPN&KOR", "AUS&NZL", "USA&CAN", "Global"]

    def __init__(
        self,
        dataPath: str,
        savePath: str,
        threshold: int = 29, 
        language: languageTemplate.LANGUAGE = "zh",
        tickSizeMultiple: float = 0
    ) -> None:
        languageTemplate.__init__(self, language, tickSizeMultiple)
        
        self.dataPath = os.path.join(dataPath, "accessibility")
        self.savePath = os.path.join(savePath, "fig_{}".format(language))
        self.threshold = threshold
        self.tickSizeMultiple = tickSizeMultiple
        
        return
    
    def plotByCountry(
        self,
        iso3s: list[str] = __regions,
        countryLevel: bool = False
    ) -> None:
        suffix = "_CountryLevel" if countryLevel else ""
        for iso3 in iso3s:
            if iso3 in self.__regions:
                dfs = []
                for c in sorted(
                        CHN if iso3 == "CHN_ALL" else
                        ASEAN if iso3 == "ASEAN" else
                        {"JPN", "KOR"} if iso3 == "JPN&KOR" else
                        {"USA", "CAN"} if iso3 == "USA&CAN" else
                        {"AUS", "NZL"} if iso3 == "AUS&NZL" else
                        GS if iso3 == "GS" else
                        EUR if iso3 == "EUR" else 
                        # os.listdir(self.dataPath)
                        CHN | ASEAN | GS | EUR | {"JPN", "KOR", "USA", "CAN", "AUS", "NZL"}
                    ):
                    path = os.path.join(self.dataPath, c, f"{c}{suffix}.csv")
                    dfs.append(pd.read_csv(path, index_col="accessibility", dtype=float)) if os.path.exists(path) else None
                df = pd.concat(dfs)
            else:
                df = pd.read_csv(
                    os.path.join(self.dataPath, iso3, f"{iso3}{suffix}.csv"),
                    index_col="accessibility"
                )
            
            self.__bar(df, iso3)

        return
    
    def __bar(self, df: pd.DataFrame, iso3: str) -> None:
        cols = [
            "population_acc1km_percentage",
            "population_acc1km_percentage_child", "population_acc1km_percentage_young",
            "population_acc1km_percentage_middle", "population_acc1km_percentage_elder",
            "population_acc1km_percentage_male", "population_acc1km_percentage_female",
            "population_acc1km_percentage_BuiltUp", "population_acc1km_percentage_Other"
        ]
        df = df[cols]

        # Group
        bins = [-np.inf, 1000, 2000, np.inf]
        labels = ["<=1 km", "1-2 km", ">2 km"]
        df["group"] = pd.cut(df.index.astype(float), bins=bins, labels=labels, right=True)
        df = df.groupby("group").sum().T
        df = df.div(df.sum(axis=1), axis=0) * 100

        df = df.loc[cols] # Change order

        # Set y position to leave blank between differnt group
        # All; Age; Gender
        ypos = [0, 2, 3, 4, 5, 7, 8, 10, 11]
        colors = ["teal", "lightseagreen", "azure"]

        _, ax = plt.figure(figsize="D")

        left = np.zeros(df.shape[0])
        n_bars = len(ypos)
        n_groups = len(labels)
        int_matrix = np.zeros((n_bars, n_groups), dtype=int)

        for bar_idx in range(n_bars):
            # 取出该条形对应的三个分段百分比（浮点值）
            segment_vals = [df[label].iloc[bar_idx] for label in labels]
            # 调用取整补偿函数，返回三个整数且和为100
            int_segments = self.__roundFix(segment_vals)
            for g_idx, int_val in enumerate(int_segments):
                int_matrix[bar_idx, g_idx] = int_val

        for i, col in enumerate(labels):
            vals = df[col]
            ax.barh(
                ypos, vals,
                left=left,
                color=colors[i],
                edgecolor="black",
                height=0.8,
                label=col
            )

            # Add value labels
            for j, (y, l, vf) in enumerate(zip(ypos, left, vals)):
                if vf >= 6:  # Do not add labels for very small segments
                    vi = int_matrix[j, i]
                    ax.text(
                        l + vf/2, y,
                        f"{vi:.0f}",
                        ha="center", va="center",
                        fontsize=TICK_SIZE*self.tickSizeMultiple,
                        fontfamily="Times New Roman",
                        color="white" if i < 2 else "#333333",
                        fontweight="bold"
                    )
            left += vals

        # Adjust legend
        ax.set_title(
            _ISO3[iso3][self.language],
            color="teal",
            fontweight="bold"
        )
        ax.set_yticks(ypos)
        ax.set_yticklabels([
            _LEGEND["bar_all"][self.language],
            _LEGEND["children"][self.language],
            _LEGEND["young"][self.language],
            _LEGEND["middle"][self.language],
            _LEGEND["elder"][self.language],
            _LEGEND["male"][self.language],
            _LEGEND["female"][self.language],
            _LEGEND["built"][self.language],
            _LEGEND["nonbuilt"][self.language]
        ])

        ax.set_xlim(0, 100)
        ax.set_xticks([])
        ax.set_xlabel('')

        # ax.legend(
        #     handles=[Patch(facecolor=color) for color in colors],
        #     labels=labels,
        #     loc="lower center",
        #     bbox_to_anchor=(0.5, -0.05),
        #     ncols=len(labels),
        # )

        # Remove edges
        for spine in ["top", "right", "bottom", "left"]:
            ax.spines[spine].set_visible(False)

        ax.tick_params(axis='y', length=0)
        ax.invert_yaxis()

        savPath = os.path.join(self.savePath, "accessibility")
        os.makedirs(savPath, exist_ok=True)
        plt.plot(savPath, "{}.jpg".format(
            "Global South" if iso3 == "GS" else
            "CHN" if iso3 == "CHN_ALL" else
            iso3
        ))

        return
    
    @staticmethod
    def __roundFix(vals, total=100):
        """将 vals 四舍五入取整，并通过调整最大项使总和等于 total"""
        intVals = [int(round(v)) for v in vals]
        diff = total - sum(intVals)
        if diff != 0:
            # 将差值加到原始值最大的分段上
            idx = np.argmax(vals)
            intVals[idx] += diff
        return intVals