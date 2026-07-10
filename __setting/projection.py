import geopandas as gpd

def EPSG(geographic: str) -> tuple[int, float, float]:
    if geographic == "AREA":
        # NSIDC EASE-Grid 2.0 Global
        return 6933, 17367530.445, 7356722.325
    
    # Default WGS84
    else:
        return 4326, 180, 90
    
# UTM
def getUtmZone(arg1: float | gpd.GeoDataFrame, arg2: float | None = None) -> str:
    if isinstance(arg1, gpd.GeoDataFrame):
        gdf = arg1
        minx, miny, maxx, maxy = gdf.total_bounds
        lon = (minx + maxx) / 2
        lat = (miny + maxy) / 2
    else:
        lat = arg1
        lon = arg2
        if not isinstance(lat, float) or not isinstance(lon, float):
            raise ValueError("Please provide (lat, lon) in float or a GeoDataFrame object.")

    zone = int((lon + 180) // 6) + 1
    hemisphere = "north" if lat >= 0 else "south"

    return f"EPSG:326{zone:02d}" if hemisphere == "north" else f"EPSG:327{zone:02d}"

CHN_ALBERS = "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"

ASIA_N_LAMBERT = "+proj=lcc +lat_1=15 +lat_2=65 +lat_0=30 +lon_0=95 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"

IBGE_ALBERS = "+proj=aea +lat_1=-2 +lat_2=-22 +lat_0=-12 +lon_0=-54 +x_0=5000000 +y_0=10000000 +ellps=GRS80 +units=m +no_defs"