import os
import numpy as np
import pandas as pd
from hdx.location.country import Country

from __setting import REGION_C, EUR, CHN, ASEAN, GS
from .byCities import analysisByCities

def exportCountryLevel(data: analysisByCities, savePath: str) -> pd.DataFrame:
    REGION = {
        "JPN": "Other_Dev",
        "KOR": "Other_Dev",
        "USA": "USA",
        "CAN": "Other_Dev",
        "AUS": "Other_Dev",
        "NZL": "Other_Dev"
    }
    for r, rname in ((EUR, "EUR"), (CHN, "CHN_ALL"), (ASEAN, "ASEAN"), (GS, "GS")):
        for i in sorted(r):
            REGION[i] = rname

    # City level data
    df = data.df[["iso3_code", "spatialConcentration"]]
    df.replace(-100, np.nan, inplace=True)
    df.dropna(how="all", inplace=True)

    # Country level data
    result = data.cdf.set_index("iso3_code").drop(columns=["geometry"]) # Using city level spatial concentration
    result.replace(-100, np.nan, inplace=True)
    result["spatialConcentration"] = np.nan

    # Add city leve data into country level
    for iso3, subdf in df.groupby("iso3_code"):
        m = subdf["spatialConcentration"].median()
        result.at[iso3, "spatialConcentration"] = m

    result.dropna(how="all", inplace=True)
    iso3s = result.index.to_series()
    result["country_en"] = iso3s.apply(Country.get_country_name_from_iso3)
    result["country_zh"] = iso3s.apply(__iso32Chinese)
    result["region"] = iso3s.map(REGION).fillna("Other")

    result["colors"] = result["region"].map(REGION_C)
    
    result.to_excel(os.path.join(savePath, "countrylevel.xlsx"))

    return result

def __iso32Chinese(iso3: str):
    if iso3 == "TWN":
        return "中国台湾"
    info = Country.get_country_info_from_iso3(iso3)
    if info is not None:
        return info.get("M49 Chinese")
    else:
        return None