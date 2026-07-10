import geopandas as gpd

def checkCRS(inputDf: gpd.GeoDataFrame, toDf: gpd.GeoDataFrame) -> None:
    if inputDf.crs != toDf.crs and toDf.crs is not None:
        inputDf.to_crs(toDf.crs, inplace=True)
    elif toDf.crs is None:
        raise RuntimeError("Input data do not define CRS.")

    return

def getCRS(path: str, layer: int | str = 0) -> int:
    from osgeo import ogr
    ogr.UseExceptions()

    ds = ogr.Open(path)
    srs = ds.GetLayer(layer).GetSpatialRef() if isinstance(layer, int) else ds.GetLayerByName(layer).GetSpatialRef()
    crs = srs.GetAuthorityCode(None)
    ds.Destroy()

    return crs