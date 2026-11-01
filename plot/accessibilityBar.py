import os, sqlite3
import pandas as pd
import numpy as np
from typing import Union, Any
from pathlib import Path
from tqdm import tqdm

from __setting import EUR, CHN, ASEAN, GS
from __plot import plt, TICK_SIZE
from __sqlite import modifyTable, spatialiteConnection
from .__template import languageTemplate
from .__text import _LEGEND, _ISO3

_GROUPS = [
    ("population_acc1km_percentage", "all"),
    ("population_acc1km_percentage_child", "child"),
    ("population_acc1km_percentage_young", "young"),
    ("population_acc1km_percentage_middle", "middle"),
    ("population_acc1km_percentage_elder", "elder"),
    ("population_acc1km_percentage_male", "male"),
    ("population_acc1km_percentage_female", "female"),
    ("population_acc1km_percentage_BuiltUp", "builtup"),
    ("population_acc1km_percentage_Other", "other")
]
# Group setting
_BINS = [-np.inf, 1000, 2000, np.inf]

class plotAcccessibilityBar(languageTemplate):
    __slots__ = ["dataPath", "savePath", "threshold", "tickSizeMultiple"]

    __regions = ["CHN_ALL", "EUR", "GS", "ASEAN", "JPN&KOR", "AUS&NZL", "USA&CAN", "Global"]

    def __init__(
        self,
        dataPath: Union[Path, str],
        savePath: Union[Path, str],
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

    def save2Gpkg(self, countryLevel: bool = False) -> None:
        # Temporary solution: only support country-level data for now
        if not countryLevel:
            raise NotImplementedError(
                "City-level accessibility requires city-specific data."
            )
        # Columns
        bands = [("<=1 km", "le1km"), ("1-2 km", "1to2km"), (">2 km", "gt2km")]
        fields = [
            (f"acc_{group}_{band}", column, label)
            for column, group in _GROUPS for label, band in bands
        ]

        suffix = "_CountryLevel" if countryLevel else ""
        idx = "iso3_code" if countryLevel else "disp_en"
        columns = [col for col, _ in _GROUPS]
        labels = [label for label, _ in bands]
        results = []

        iso3s = sorted(os.listdir(self.dataPath))

        for iso3 in tqdm(iso3s, desc="Saving accessibility bar to GPKG", unit="country"):
            dataPath = os.path.join(self.dataPath, iso3, f"{iso3}{suffix}.csv")
            if not os.path.isfile(dataPath):
                continue
            df = pd.read_csv(dataPath, index_col="accessibility", dtype=float)

            # Group by accessibility distance
            df = df[columns]
            df["group"] = pd.cut(
                df.index.astype(float),
                bins=_BINS,
                labels=labels,
                right=True
            )

            # Calculate percentages
            df = df.groupby(
                "group", observed=False
            )[columns].sum().T

            df = df.reindex(
                index=columns, columns=labels, fill_value=0
            )
            df = df.div(
                df.sum(axis=1).replace(0, np.nan), axis=0
            ) * 100

            # Flatten into one record per country
            result: dict[str, object] = {idx: iso3}
            result.update({
                name: df.at[column, label]
                for name, column, label in fields
            })
            results.append(result)

        if not results:
            raise ValueError("No accessibility CSV files found.")

        # Complete country-level result DataFrame
        resultDF = pd.DataFrame(
            results,
            columns=[idx] + [name for name, _, _ in fields]
        )
        self.__updateData(
            resultDF,
            *((name, "REAL", None, False) for name, _, _ in fields),
            table="result_country" if countryLevel else "result",
            idx=idx
        )

        return

    def __updateData(
        self,
        df: pd.DataFrame,
        *fields: tuple[str, str, Any, bool], table: str,
        idx: str,
    ) -> None:
        conn = sqlite3.connect(
            os.path.join(os.path.dirname(self.dataPath), "result.gpkg"),
            factory=spatialiteConnection
        )

        conn.loadSpatialite() # Load spatialite extension
        cursor = conn.cursor(factory=modifyTable)
        # Add field
        ## ("affectedIncident", "Text", None, False)
        ## fieldName, colType, initialValue, whetherIndex
        cursor.addFields(table, *fields)
        # Fid not continue, using unique disp_en or iso3_code as index
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{idx} ON {table} ({idx})")
        conn.commit()

        # Add data
        columns = [idx] + [field[0] for field in fields]
        df[columns].to_sql(
            "tempTable", conn,
            if_exists="replace", index=False, method="multi",
            chunksize=32766//len(columns) # Max chunksize is 32766 for all threads
        )
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{idx} ON tempTable ({idx})")
        conn.commit()
        conn.execute("BEGIN TRANSACTION;")

        # Update all fields in one SQL statement
        assignments = ", ".join(
            f'"{name}" = tempTable."{name}"'
            for name in columns[1:]
        )
        cursor.execute(
            f"""
            UPDATE "{table}"
            SET {assignments}
            FROM tempTable
            WHERE tempTable."{idx}" = "{table}"."{idx}"
            """
        )

        cursor.execute("DROP TABLE IF EXISTS tempTable")
        conn.commit()
        conn.execute("VACUUM")
        conn.close()

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
        cols = [x[1] for x in _GROUPS]
        df = df[cols]

        # Group
        labels = ["<=1 km", "1-2 km", ">2 km"]
        df["group"] = pd.cut(df.index.astype(float), bins=_BINS, labels=labels, right=True)
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
        n__GROUPS = len(labels)
        int_matrix = np.zeros((n_bars, n__GROUPS), dtype=int)

        for bar_idx in range(n_bars):
            # Retrieve the three segment percentages (floating) corresponding to the bar
            segment_vals = [df[label].iloc[bar_idx] for label in labels]
            # Call the rounding compensation function to return three integers that sum to 100
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
        """
        Round the values in vals to the nearest integer,
        and adjust the largest element so that the sum equals total
        """
        intVals = [int(round(v)) for v in vals]
        diff = total - sum(intVals)
        if diff != 0:
            # Add the difference to the segment with the largest original value
            idx = np.argmax(vals)
            intVals[idx] += diff
        return intVals