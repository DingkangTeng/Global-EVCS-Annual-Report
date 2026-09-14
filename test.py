

if __name__ == "__main__":
    import os 
    import pandas as pd
    from analysis import analysisByCities
    RESULTS_ROOT = r"C:\0_PolyU\Global EVCS Annual Report 2026\data"
    EVCS_GPKG = r"C:\0_PolyU\data-global-ev-2026\__Data\Global_Country_2026\merge.gpkg"
    POI = r"D:\globalPOI_2025\extract_withCountry.parquet"
    POP = r"D:\Population_Related\global_2025"
    POP_GLOBAL = r"D:\Population_Related\global_pop_2025_CN_1km_R2025A_UA_v1.tif"

    CITIES = analysisByCities(
        RESULTS_ROOT, # Save path
        r"C:\0_PolyU\boundary.gpkg", # Boundary
        r"D:\0_Project_BackupData\0_Finished\Global EV Acc Patterns\__Data\urbanArea\builtUpArea_fixGeom.gpkg" # Built-up area
    )

    from analysis import spatialConcentration_Country
    # Country level concnetration
    spatialConcentration_Country(CITIES)

    MAP_ELEMENT = r"C:\0_PolyU\Globa EVCS Annual Report 2025\ArcGIS\Globa EVCS Annual Report 2025.gdb"
    FIG_ROOT = r"C:\0_PolyU\Global EVCS Annual Report 2026"
    from plot import plotCities
    LAGUAGE = "en"
    plot = plotCities(CITIES, MAP_ELEMENT, FIG_ROOT, LAGUAGE)
    # 聚集度、空间分布的条形图和热力图
    plot.drawOverall()

    plot.spatialConcentration("CHN")
    plot.spatialConcentration("USA")
    plot.spatialConcentration("EUR")

    plot.spatialCoverage("CHN")
    plot.spatialCoverage("USA")
    plot.spatialCoverage("EUR")

    plot.spatialCoverageForPop("CHN")
    plot.spatialCoverageForPop("USA")
    plot.spatialCoverageForPop("EUR")

    from plot import plotAcccessibilityBar
    plotAcccessibilityBar(RESULTS_ROOT, FIG_ROOT, language=LAGUAGE, tickSizeMultiple=1.5).plotByCountry(countryLevel=True)

    # import os 
    # import pandas as pd
    # from analysis import analysisByCities
    # RESULTS_ROOT = r"C:\0_PolyU\Globa EVCS Annual Report 2025\data"
    # FIG_ROOT = r"C:\0_PolyU\Globa EVCS Annual Report 2025"
    # PLOT_ROOT = r"C:\0_PolyU\Globa EVCS Annual Report 2025\plot"
    # EVCS_GPKG = r"C:\0_PolyU\data-global-ev-2025\__Data\Global_Country_2025\merge.gpkg"
    # POI = r"D:\globalPOI_2025\extract_withCountry.parquet"
    # POP = r"D:\Population_Related\global_2025"
    # MAP_ELEMENT = r"C:\0_PolyU\Globa EVCS Annual Report 2025\ArcGIS\Globa EVCS Annual Report 2025.gdb"

    # CITIES = analysisByCities(
    #     RESULTS_ROOT,
    #     r"C:\0_PolyU\boundary.gpkg", # Boundary
    #     r"C:\0_PolyU\data-global-ev-2025\__Data\urbanArea\builtUpArea_fixGeom.gpkg" # Built-up area
    # )

    # LAGUAGE = "zh"

    # from plot import plotAcccessibilityBar
    # plotAcccessibilityBar(RESULTS_ROOT, FIG_ROOT, language=LAGUAGE, tickSizeMultiple=1.5).plotByCountry(iso3s=["Global"], countryLevel=True)

    # from osgeo import ogr
    # def rename_column_ogr(gpkg_path, layer_name, old_name, new_name):
    #     # 打开数据集（可更新模式）
    #     ds = ogr.Open(gpkg_path, update=1)
    #     if ds is None:
    #         print("无法打开文件")
    #         return
        
    #     for i in range(ds.GetLayerCount()):
    #         layer = ds.GetLayer(i)
    #         print(f"图层 {i}: {layer.GetName()}")
        
    #     # 直接执行 SQL 重命名语句
    #     sql = f'ALTER TABLE "{layer_name}" RENAME COLUMN "{old_name}" TO "{new_name}"'
    #     ds.ExecuteSQL(sql)
        
    #     # 关闭数据集
    #     ds = None

    # # 使用示例
    # rename_column_ogr(r"C:\0_PolyU\Globa EVCS Annual Report 2025\data\result.gpkg", "result", "spatialConentration_Other", "spatialConcentration_Other")