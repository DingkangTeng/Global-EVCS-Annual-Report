import numpy as np
import pandas as pd

from __setting import CHN, EUR, ASEAN, GS
from analysis import analysisByCities

def cityStatistic(data: analysisByCities, cols: list[str]) -> None:
    df = data.df[["iso3_code"] + cols]
    n = len(cols)

    result = np.empty([6, n], dtype=np.uint32)
    for col in range(n):
        for row, countries in enumerate([
                CHN, {"USA"}, EUR, ASEAN, {"JPN", "KOR", "AUS", "NZL"}, GS
            ]):
                subdf = df.loc[df["iso3_code"].isin(countries)].dropna()
                subdf = subdf.loc[subdf[cols[col]] != -100]
                result[row, col] = subdf.shape[0]

    print(pd.DataFrame(
        result,
        columns=cols,
        index=pd.Index(
            [u"1.中国", u"2.美国", u"3.欧洲", u"4.东盟", u"5.其他发达国家", u"6.全球南方国家"],
            name="指标"
        )
    ))

    return