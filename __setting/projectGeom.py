from pyproj import Transformer, CRS
from shapely.ops import transform
from shapely.geometry.base import BaseGeometry
from typing import Any

# Project single geom
def projectGeom(geom: BaseGeometry, crsFrom: Any, crsTo: Any) -> BaseGeometry:
    if CRS(crsFrom) == CRS(crsTo):
        return geom
    
    else:
        transformer = Transformer.from_crs(crsFrom, crsTo, always_xy=True)
        return transform(transformer.transform, geom)