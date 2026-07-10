import os
import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio as rio
from rasterio import features, windows, warp
from tqdm import tqdm
from shapely.geometry.base import BaseGeometry
from concurrent.futures import as_completed, ProcessPoolExecutor
from typing import Any

from .byCities import analysisByCities

MAX_DISTANCE = 30000 * 100  # 30 km in centimeters
__COLS = (
    "acc1km_percentage",
    "acc1km_percentage_male", "acc1km_percentage_female",
    "acc1km_percentage_child", "acc1km_percentage_young", "acc1km_percentage_middle", "acc1km_percentage_elder",
    "acc1km_percentage_BuiltUp", "acc1km_percentage_Other"
)
    
def accessibility_Country(
    data: analysisByCities, pop: str,
    savePath: str,
    blockSize: int = 4096
) -> None:
    df = data.cdf

    # Check crs
    if df.crs is not None and df.crs.to_epsg() != 4326:
        df.to_crs(4326, inplace=True)
    elif df.crs is None:
        raise RuntimeError("Input data do not have CRS.")

    savePath = os.path.join(savePath, "accessibility")
    bar = data.bar("Analysising accessibility", multiple=7, countryLevel=True)

    # Get built-up area
    builtUpAll = gpd.read_file(data.builtup, layer="builtup", columns=["iso3", "geometry"])
    if builtUpAll.crs is not None and builtUpAll.crs.to_epsg() != 4326:
        builtUpAll = builtUpAll.to_crs(4326)
    elif builtUpAll.crs is None:
        raise RuntimeError("Input built-up area data do not have CRS.")

    # Process by country group
    for row in df[["iso3_code", "geometry"]].itertuples():
        iso3 = getattr(row, "iso3_code")
        geom: BaseGeometry = getattr(row, "geometry")
        bar.set_postfix(iso3=iso3)

        popPaths = (
            os.path.join(
                pop,
                "population_All",
                "{}_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_Male",
                "{}_['m']_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_Female",
                "{}_['f']_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_children",
                "{}_allGender_[0, 1, 5, 10, 15]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_young",
                "{}_allGender_[20, 25, 30, 35, 40]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_middle",
                "{}_allGender_[45, 50, 55]_merge.tif".format(iso3)
            ),
            os.path.join(
                pop,
                "population_All_elderly",
                "{}_allGender_[60, 65, 70, 75, 80, 85, 90]_merge.tif".format(iso3)
            )
        )

        if not os.path.exists(popPaths[0]):
            bar.update(7)
            continue

        accPath = os.path.join(savePath, str(iso3))
        countryResult = os.path.join(accPath, "{}_CountryLevel.csv".format(iso3))

        # Have population raster, accessibility raster, and do not have conuntry level result
        if os.path.exists(accPath) and not os.path.exists(countryResult):
            futures = []
            with ProcessPoolExecutor(max_workers=7) as executor:
                for i, popPath in enumerate(popPaths):
                    if i == 0:
                        builtUp = gpd.GeoSeries(
                            builtUpAll[builtUpAll["iso3"] == iso3].geometry,
                            crs=builtUpAll.crs
                        )
                    else:
                        builtUp = None
                    futures.append(
                        executor.submit(
                            _processByCountry,
                            geom, iso3, __COLS[i], accPath, popPath,
                            i == 0, builtUp,
                            blockSize
                        )
                    )

                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result) if result is not None else None
                        bar.update()
                    except Exception as e:
                        raise RuntimeError(f"Error processing country {iso3}: {e}")
            
            # # Single Thread
            # results = []
            # for i, popPath in enumerate(popPaths):
            #     if i == 0:
            #         builtUp = gpd.GeoSeries(
            #             builtUpAll[builtUpAll["iso3"] == iso3].geometry,
            #             crs=builtUpAll.crs
            #         )
            #     else:
            #         builtUp = None
            #     result = self._processByCountry(
            #         geom, iso3, self.__COLS[i], accPath, popPath,
            #         i == 0, builtUp,
            #         blockSize
            #     )
            #     results.append(result) if result is not None else None
            #     bar.update()
            
            # Save
            accCountry = pd.concat(results, axis=1) if len(results) > 0 else pd.DataFrame()
            if not accCountry.empty:
                accCountry.sort_index().fillna(0).to_csv(countryResult, encoding="utf-8", index_label="accessibility")
        
        else:
            bar.update(7)
    
    bar.close()

    return

def _processByCountry(
    geom: BaseGeometry, iso3: str, col: str,
    accPath: str, popPath: str,
    calUrbanArea: bool, builtUp: gpd.GeoSeries | None = None,
    blockSize: int = 2048
) -> pd.DataFrame | None:
    # Check data
    tifPath = os.path.join(accPath, "{}.tif".format(iso3))
    belowThres = os.path.join(accPath, "{}.txt".format(iso3))

    ## Skip no accessibility data country
    if os.path.exists(belowThres):
        return
    elif not os.path.exists(tifPath):
        return
    
    # Process
    with (
        rio.Env(GDAL_NUM_THREADS="ALL_CPUS"),
        rio.open(popPath) as src,
        rio.open(tifPath) as srcAcc
    ):
        # Unify projection
        crs = src.crs
        if crs.to_epsg() != 4326:
            raise RuntimeError("Input population data is not WGS84")
    
        # rows, cols = src.height, src.width
        transform = src.transform
        nodata = src.nodata

        # Get city population raster
        window = windows.from_bounds(*geom.bounds, transform).round_offsets().round_lengths()
        window = window.intersection(
            windows.Window(0, 0, src.width, src.height) # type: ignore
        )
        windowH = int(window.height)
        windowW = int(window.width)
        rowStart = max(0, int(window.row_off))
        colStart = max(0, int(window.col_off))
        aligned = (srcAcc.transform == src.transform) and (srcAcc.shape == src.shape)
        
        # rowStop = min(rows, rowStart + int(window.height))
        # colStop = min(cols, colStart + int(window.width))
        # window = windows.Window(colStart, rowStart, colStop - colStart, rowStop - rowStart) # type: ignore
        # windowH = rowStop - rowStart
        # windowW = colStop - colStart

        ## Get max index
        stats = srcAcc.stats(indexes=1)[0]
        maxIdx = min(
            int(stats.max * 100 if (stats.max is not None and not np.isnan(stats.max)) else MAX_DISTANCE),
            MAX_DISTANCE
            ) + 2
        del stats

        # Calculate built up
        if calUrbanArea:
            popTotalAcc = np.zeros([3, maxIdx], dtype=np.float64)
        else:
            popTotalAcc = np.zeros([1, maxIdx], dtype=np.float64)
        
        total = (windowH // blockSize + 1) * (windowW // blockSize + 1)
        bar = tqdm(total=total, desc=f"Processing {iso3} - {col}", unit="block") if total > 20 else None

        for y in range(0, windowH, blockSize):
            for x in range(0, windowW, blockSize):
                # 当前块的宽高
                w = min(blockSize, windowW - x)
                h = min(blockSize, windowH - y)
                blockWindow = windows.Window(
                    colStart + x, rowStart + y, w, h # type: ignore
                )
                # 读取人口块
                popBlock = src.read(1, window=blockWindow)
                # 读取可达性块（假设两栅格完全对齐）
                if aligned:
                    accBlock = srcAcc.read(1, window=blockWindow)
                    blockTrans = src.window_transform(blockWindow)
                else:
                    # 重采样到与人口块相同的形状和变换
                    accBlock = np.zeros((h, w), dtype=np.float64)
                    blockTrans = src.window_transform(blockWindow)
                    warp.reproject(
                        source=rio.band(srcAcc, 1),
                        destination=accBlock,
                        src_transform=srcAcc.transform,
                        src_crs=srcAcc.crs,
                        dst_transform=blockTrans,
                        dst_crs=src.crs,
                        resampling=warp.Resampling.nearest,
                        src_nodata=srcAcc.nodata,
                        dst_nodata=srcAcc.nodata
                    )

                # 几何掩膜
                _processBlock(
                    popBlock, accBlock, blockTrans,
                    geom, builtUp,
                    h, w, blockWindow, nodata,
                    calUrbanArea,
                    popTotalAcc
                )

                bar.update() if bar is not None else None
        bar.close() if bar is not None else None

        # Simplify result
        valid_idx = np.where(popTotalAcc[0] > 0)[0]
        if len(valid_idx) == 0:
            return None
        
        result = {"population_{}".format(col): np.round(popTotalAcc[0][valid_idx], 2)}
        if calUrbanArea:
            result["population_{}_BuiltUp".format(col)] = np.round(popTotalAcc[1][valid_idx], 2)
            result["population_{}_Other".format(col)] = np.round(popTotalAcc[2][valid_idx], 2)

    result = pd.DataFrame(result, index=valid_idx / 100.0)
    result.index.name = "accessibility"

    return result


def _processBlock(
    popBlock: np.ndarray, accBlock: np.ndarray, blockTrans: Any,
    geom: BaseGeometry, builtUp: gpd.GeoSeries | None,
    h: int, w: int, blockWindow: windows.Window, nodata: Any,
    calUrbanArea: bool,
    popTotalAcc: np.ndarray
) -> None:
    geomMask = features.geometry_mask(
        [geom],
        out_shape=(h, w),
        transform=blockTrans,
        invert=True
    )

    # 有效像素掩膜
    valid = ~np.isnan(popBlock) & ~np.isnan(accBlock)
    if nodata is not None:
        valid &= (popBlock != nodata)
    # 假设 acc 的 nodata 已在前面检查过（有 nan 即无效）
    valid &= geomMask

    if not np.any(valid):
        return

    # 提取有效数据
    popValid = popBlock[valid]
    accValid = accBlock[valid]
    accValid = np.round(accValid * 100).astype(np.uint32)
    accValid[accValid >= MAX_DISTANCE] = MAX_DISTANCE
    np.add.at(popTotalAcc[0], accValid, popValid)

    if calUrbanArea:
        # 计算当前块的建成区掩膜
        if builtUp is not None and not builtUp.empty:
            # # 仅对与 builtupGeom 有交集的块做栅格化，提高效率
            # possible = builtUp.sindex.intersection(
            #     windows.bounds(blockWindow, blockTrans)
            # )
            
            # # 简单起见直接栅格化整个小块，geometry_mask 会自动处理超出边界的部分
            # if possible.size > 0:
            #     builtupMask = features.geometry_mask(
            #         builtUp.iloc[possible],
            #         out_shape=(h, w),
            #         transform=blockTrans,
            #         invert=True,
            #         all_touched=False
            #     )[valid]
            # else:
            #     builtupMask = np.zeros(popValid.shape, dtype=np.bool)
            builtupMask = features.geometry_mask(
                builtUp,
                out_shape=(h, w),
                transform=blockTrans,
                invert=True
            )[valid]
        else:
            builtupMask = np.zeros(popValid.shape, dtype=np.bool)

        np.add.at(popTotalAcc[1], accValid, popValid * builtupMask) # Built-up
        np.add.at(popTotalAcc[2], accValid, popValid * (~builtupMask)) # Non built-up
        
        # # Debug
        # if builtupMask.sum() > 0:
        #     pop_in_builtup = popValid[builtupMask].sum()
        #     print(f"  建成区掩膜像素数: {builtupMask.sum()}, 人口总和: {pop_in_builtup}")
        #     print(f"最终 popTotalAcc[1] 总和: {popTotalAcc[1].sum()}")
        #     print(f"popTotalAcc 第1行非零个数: {np.count_nonzero(popTotalAcc[1])}")
        #     print(popTotalAcc)

    return