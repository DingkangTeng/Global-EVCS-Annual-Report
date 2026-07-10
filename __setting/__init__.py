from .checkCRS import checkCRS, getCRS
from .projectGeom import projectGeom
from .projection import EPSG, getUtmZone, CHN_ALBERS, ASIA_N_LAMBERT, IBGE_ALBERS
from .stdCityName import stdCityName

# Constant
EUR = {
    "AUT", "BEL", "BGR", "CHE", "CZE", "DEU", "DNK", "EST", "GRC", "ESP",
    "FIN", "FRA", "HRV", "HUN", "ISL", "ITA", "LTU", "LUX", "LVA", "NLD",
    "NOR", "POL", "PRT", "ROU", "SWE", "SVN", "SVK", "CYP", "IRL", "MLT",
    "GBR", "LIE"
}

CHN = {"CHN", "TWN", "MAC", "HKG"}

ASEAN = {
    "BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "VNM" #, "TLS"
}

GS = {"ZAF", "BRA", "MEX"}

# Region colors
REGION_C = {
    "CHN_ALL": "#cd3333",
    "USA": "#9932cc",
    "EUR": "gold",
    "ASEAN": "#458b00",
    "Other_Dev": "teal",
    "GS": "#ee1289"
    # "JPN&KOR": "teal",
    # "USA&CAN": "#9932cc",
    # "AUS&NZL": "dodgerblue",
    # "Other": "gray"
}