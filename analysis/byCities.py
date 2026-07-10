import os, sqlite3
import geopandas as gpd
from tqdm import tqdm
from typing import Any

from __sqlite import modifyTable, spatialiteConnection

UEXCEPT_ISO = {
    "ATA",
    "xxx",
    "xUK", "xSR", "xSK", "xSI", "xSI", "xPI", "xMS", "xKI", "xJL", "xJK", "xIT", "xHT", "xFR", "xAP", "xAC", "xAB"
}

class analysisByCities:
    __slots__ = ["savePath", "gpkg", "boundary", "builtup", "df", "cdf", "layer"]

    def __init__(self, savePath: str, boundary: str, builtup: str, layer: str = "result", override: bool = False) -> None:
        self.savePath = savePath
        self.gpkg = os.path.join(savePath, "result.gpkg")
        self.boundary = boundary
        self.builtup = builtup
        self.layer = layer

        clayer= "{}_country".format(layer)
        overrides = [True, True] if override else [False, False]

        # Load existing data
        if os.path.exists(self.gpkg) and not override:
            layers = set(gpd.list_layers(self.gpkg)["name"].to_list())
            if layer in layers:
                print("Loading city level data...")
                self.df = gpd.read_file(self.gpkg, layer=layer, encoding="utf-8")
            else:
                overrides[0] = True
            if clayer in layers:
                print("Loading country level data...")
                self.cdf = gpd.read_file(self.gpkg, layer=clayer, encoding="utf-8")
            else:
                overrides[1] = True

        # Creat city level result
        if overrides[0]:
            print("Creating city level data...")
            self.df = gpd.read_file(boundary, layer="boundary", encoding="utf-8")[["disp_en", "iso3_code", "geometry"]]
            self.df = self.df[self.df["iso3_code"] != "ATA"].reset_index(drop=True)
            self.overrideData(overrideLevel="city")
        # Creat country level result 
        if overrides[1]:
            print("Creating country level data...")
            self.cdf = gpd.read_file(boundary, layer="level1", encoding="utf-8")[["iso3_code", "geometry"]]
            self.cdf = self.cdf[~self.cdf["iso3_code"].isin(UEXCEPT_ISO)].reset_index(drop=True)
            self.overrideData(overrideLevel="country")

        return
    
    def updateData(self, *fields: tuple[str, str, Any, bool], table: str = "", countryLevel: bool = False) -> None:
        # Get city level or country level table
        table = ("{}_country".format(self.layer) if countryLevel else self.layer) if table == "" else table
        df = self.cdf if countryLevel else self.df
        idx = "iso3_code" if countryLevel else "disp_en"

        conn = sqlite3.connect(self.gpkg, factory=spatialiteConnection)
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
        for fieldName in columns:
            cursor.execute(
                f"""
                UPDATE {table}
                SET {fieldName} = tempTable.{fieldName}
                    FROM tempTable 
                    WHERE tempTable.{idx} = {table}.{idx}
                """
            )
        cursor.execute("DROP TABLE IF EXISTS tempTable")
        conn.commit()
        conn.execute("VACUUM")
        conn.close()

        return
    
    def overrideData(self, layer: str = "", overrideLevel: str = "all") -> None:
        raisee = True
        # City level result
        if overrideLevel in {"city", "all"}:
            self.df.to_file(
                self.gpkg,
                layer=self.layer if layer == "" else layer,
                encoding="utf-8"
            )
            raisee = False

        # Country level result
        if overrideLevel in {"country", "all"}:
            self.cdf.to_file(
                self.gpkg,
                layer="{}_country".format(self.layer) if layer == "" else "{}_country".format(layer),
                encoding="utf-8"
            )
            raisee = False
        
        # Error
        if raisee:
            raise ValueError("overrideLevel must be \"city\", \"country\", or \"all\".")

        return
    
    def bar(self, desc: str, addition: float = 0, multiple: float = 1, countryLevel: bool = False) -> tqdm:
        if countryLevel:
            return tqdm(total=self.cdf.shape[0] * multiple + addition, desc=desc, unit="country")
        else:
            return tqdm(total=self.df.shape[0] * multiple + addition, desc=desc, unit="city")
    
    @property
    def crs(self) -> int:
        crs = self.df.crs
        crs = 4326 if crs is None else crs.to_epsg()
        crs = 4326 if crs is None else crs

        return crs