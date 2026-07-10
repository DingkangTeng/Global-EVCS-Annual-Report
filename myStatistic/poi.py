import pandas as pd
import numpy as np

from __setting import CHN, EUR, ASEAN, GS

def poiStatistic(poi: str) -> None:
    df = pd.read_parquet(poi, filters=[("fsq_category_ids", "in", [1, 2, 3])]).groupby("fsq_category_ids")
    result = np.empty([6, 3], dtype=np.uint32)

    for ids, subPOI in df:
        col = int(np.asarray(ids).item()) - 1

        for row, countries in enumerate([
            CHN, {"USA"}, EUR, ASEAN, {"JPN", "KOR", "AUS", "NZL"}, GS
        ]):
            subdf = subPOI.loc[subPOI["level1"].isin(countries)]
            result[row, col] = subdf.shape[0]

    print(pd.DataFrame(
        result,
        columns=[u"管理", u"商业", u"休憩"],
        index=pd.Index(
            [u"1.中国", u"2.美国", u"3.欧洲", u"4.东盟", u"5.其他发达国家", u"6.全球南方国家"],
            name="POI数"
        )
    ))

    return