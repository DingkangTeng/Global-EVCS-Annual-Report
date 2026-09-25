# Global EVCS Annual Report

This repository contains the geospatial analysis and visualization workflow developed for the **Global Electric Vehicle Charging Station (EVCS) Annual Report**. The current implementation supports the **2025 annual report** and evaluates public charging infrastructure at both city and country scales.

The workflow integrates EV charging-station locations with population rasters, points of interest (POIs), built-up areas, administrative boundaries, and renewable-energy rasters to evaluate:

- spatial distribution and concentration;
- geographic, population, and POI coverage;
- charging-station accessibility;
- spatial equity;
- solar- and wind-energy potential; and
- publication-ready maps and statistical figures.

The primary workflow is implemented in [`main_2025.ipynb`](main_2025.ipynb). For the bundled USA example, start with [`sample.ipynb`](sample.ipynb).

---

## Workflow Overview

```text
Input datasets
      │
      ▼
analysisByCities
      │
      ├── City-level analysis table
      └── Country-level analysis table
      │
      ▼
RESULTS_ROOT/result.gpkg
      │
      ├── Spatial concentration
      ├── Spatial coverage
      ├── Accessibility
      ├── Spatial equity
      └── Renewable-energy potential
      │
      ▼
Numerical and raster outputs
      │
      ▼
Plotting APIs
      │
      ▼
FIG_ROOT/fig_en/ or FIG_ROOT/fig_zh/
```

---

## Installation and Sample Data

### Python Requirements

The project's pinned Python dependencies are listed in [`requirements.txt`](requirements.txt):

| Package | Version |
|---|---|
| GDAL | 3.12.2 |
| GeoPandas | 1.1.3 |
| Matplotlib | 3.11.2 |
| matplotlib-scalebar | 0.9.0 |
| NumPy | 2.5.3 |
| pandas | 3.0.6 |
| pyproj | 3.7.2 |
| Rasterio | 1.5.0 |
| scikit-learn | 1.9.1 |
| SciPy | 1.18.1 |
| Seaborn | 0.13.2 |
| Shapely | 2.1.2 |
| tqdm | 4.67.3 |
| HDX Python API | 6.7.0 |

### Sample Data

The repository includes [`requirements.txt`](requirements.txt), [`sample.ipynb`](sample.ipynb), and [`__sampleData/`](__sampleData/). The notebook uses paths relative to the **repository root**. The checked-in notebooks record Python 3.14.3 as their authoring environment; the dependency versions in `requirements.txt` are pinned, so use a compatible Python installation.

1. Clone the repository and work from its root directory:

   ```bash
   git clone https://github.com/DingkangTeng/Global-EVCS-Annual-Report.git
   cd Global-EVCS-Annual-Report
   python -m venv .venv
   ```

2. Activate the virtual environment and install dependencies. In **Windows PowerShell**:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

   In **macOS/Linux**, activate it with `source .venv/bin/activate`, then run the same two `python -m pip install` commands. The pinned `gdal` package may require a compatible local GDAL installation on some systems; installation of the Python packages alone does not guarantee support for all GIS data drivers.

3. Launch `python -m jupyterlab` from the repository root, select the virtual environment's Python kernel, open `sample.ipynb`, and run its cells in order. Its first cell sets `RESULTS_ROOT = r"__sampleData\data"` and `FIG_ROOT = r"__sampleData"`. The notebook paths use Windows backslashes: on macOS/Linux, change these paths to forward slashes or construct them with `pathlib.Path`.

4. Inspect the generated outputs in `__sampleData/data/` and figures in `__sampleData/fig_en/`. The repository already includes sample outputs; rerunning the analysis can overwrite them.

The sample covers a limited USA study area (Los Angeles, California), so use `"USA"` for maps and `iso3s=["USA"]` for accessibility bars. `plot.drawOverall()` can produce charts, but its country rankings on this sample are not global report results. For the complete study, obtain the remaining country inputs and edit the absolute paths in `main_2025.ipynb`.

---

## Path Configuration

The notebook defines two independent output roots:

```python
RESULTS_ROOT = r"path\to\analysis_results"
FIG_ROOT = r"path\to\figures"
```

### `RESULTS_ROOT`

`RESULTS_ROOT` stores analysis results, intermediate rasters, and the renewable-energy rasters required by the current implementation. It does **not** have to be a directory named `data`; its location is determined by the constant in `main_2025.ipynb`.

```text
<RESULTS_ROOT>/
├── result.gpkg                         # Generated
├── evcs.tif                            # Generated
├── countrylevel.xlsx                   # Generated
├── accessibility/                      # Generated
│   └── <ISO3>/
│       ├── <ISO3>.tif
│       └── <ISO3>_CountryLevel.csv
├── lorenz/                            # Generated
│   └── <ISO3>/
│       └── <ISO3>_CountryLevel.csv
├── GHI/
│   └── GHI.tif                         # Required input
└── wind_speed_cog_10m.tif              # Required input
```

### `FIG_ROOT`

`FIG_ROOT` is the root directory for generated figures. Plotting APIs append a language-specific directory automatically:

```text
language="en"  →  <FIG_ROOT>/fig_en/
language="zh"  →  <FIG_ROOT>/fig_zh/
```

Typical structure:

```text
<FIG_ROOT>/
├── fig_en/
│   ├── CHN/
│   ├── USA/
│   ├── EUR/
│   └── accessibility/
└── fig_zh/
    ├── CHN/
    ├── USA/
    ├── EUR/
    └── accessibility/
```

Only the language folders requested by the user need to exist.

---

## Project Structure

```text
Global-EVCS-Annual-Report/
├── analysis/       # City/country analyses and result export
├── raster/         # EVCS and accessibility raster generation
├── plot/           # Maps and statistical figures
├── __plot/         # Shared plotting utilities
├── __setting/      # CRS, projection, and regional definitions
├── __sqlite/       # SQLite/SpatiaLite utilities
└── main_2025.ipynb # Main annual workflow
```

---

## Input Data

### EV Charging Stations

The EVCS GeoPackage must contain an `evcs` layer. The workflow uses fields including:

- `level1`: ISO3 country identifier;
- `geometry`: charging-station point geometry.

```python
EVCS_GPKG = r"path\to\evcs.gpkg"
```

### Administrative Boundaries

The boundary GeoPackage used by `analysisByCities` must contain:

- `boundary`: city-level analytical units;
- `level1`: country-level analytical units;
- `level2`: subnational boundaries used primarily for mapping.

### Built-Up Areas

The built-up-area GeoPackage must contain a `builtup` layer. Built-up areas are used particularly in accessibility analyses to distinguish built-up and non-built-up populations.

### Points of Interest

POI data are read from a Parquet file:

```python
POI = r"path\to\poi.parquet"
```

The current workflow analyzes three POI groups identified by `fsq_category_ids` values `1`, `2`, and `3`. Their coverage results are stored as three separate indicators.

---

## Population Raster Data

Population data are required for spatial-coverage and accessibility analyses. The current code expects a strict directory structure and filename convention.

```python
POP = r"path\to\population"
```

```text
<POP>/
├── population_All/
├── population_Male/
├── population_Female/
├── population_All_children/
├── population_All_young/
├── population_All_middle/
└── population_All_elderly/
```

Every filename begins with an ISO 3166-1 alpha-3 code such as `USA`, `CHN`, `DEU`, `JPN`, or `BRA`.

| Group | Directory | Required filename suffix |
|---|---|---|
| Total | `population_All` | `allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif` |
| Male | `population_Male` | `['m']_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif` |
| Female | `population_Female` | `['f']_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif` |
| Children | `population_All_children` | `allGender_[0, 1, 5, 10, 15]_merge.tif` |
| Young | `population_All_young` | `allGender_[20, 25, 30, 35, 40]_merge.tif` |
| Middle-aged | `population_All_middle` | `allGender_[45, 50, 55]_merge.tif` |
| Elderly | `population_All_elderly` | `allGender_[60, 65, 70, 75, 80, 85, 90]_merge.tif` |

The complete filename is `{ISO3}_{suffix}`. For example:

```text
USA_allGender_[0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]_merge.tif
```

Brackets, spaces, commas, quotation marks, and suffixes are part of the current naming convention and must be preserved.

---

## Renewable-Energy Raster Data

Renewable-energy analysis requires two rasters at fixed locations relative to `RESULTS_ROOT`:

```text
<RESULTS_ROOT>/GHI/GHI.tif
<RESULTS_ROOT>/wind_speed_cog_10m.tif
```

These paths are used by both the renewable-energy analysis and the raw renewable-energy mapping workflow.

---

## API Reference

The following APIs are used directly by `main_2025.ipynb`.

### `analysisByCities`

```python
from analysis import analysisByCities

CITIES = analysisByCities(RESULTS_ROOT, BOUNDARY, BUILTUP)
```

Creates the central analysis object used by subsequent APIs. `CITIES.df` stores city-level results and `CITIES.cdf` stores country-level results.

Important parameters:

- `savePath`: analysis output root, normally `RESULTS_ROOT`;
- `boundary`: boundary GeoPackage;
- `builtup`: built-up-area GeoPackage;
- `layer`: result-layer name, defaulting to `result`;
- `override`: recreates existing result tables when `True`.

It creates or loads `<RESULTS_ROOT>/result.gpkg`, normally containing the `result` and `result_country` layers. Later analysis APIs add indicators to these layers.

### `creatEVCS`

```python
from raster import creatEVCS

creatEVCS(EVCS_GPKG, RESULTS_ROOT)
```

Rasterizes EV charging-station points into a regular grid. With the default `gridSize=1000`, each 1 km × 1 km cell records the number of charging stations within it.

Output:

```text
<RESULTS_ROOT>/evcs.tif
```

### `spatialConcentration`

```python
from analysis import spatialConcentration

spatialConcentration(CITIES)
```

Measures how strongly charging stations are concentrated within each city using `<RESULTS_ROOT>/evcs.tif`. The current implementation compares the number of stations in the highest-density 10% of occupied raster cells with the city's total EVCS count.

The result is stored in the city-level `spatialConcentration` field. Geographic units below the configured minimum EVCS threshold receive the internal invalid-data value `-100`.

### `spatialCoverage`

```python
from analysis import spatialCoverage

spatialCoverage(CITIES, EVCS_GPKG, POI, POP, maxThread=8)
```

Calculates city-level charging-infrastructure coverage. By default, a 1,000 m buffer is generated around EV charging stations and used to measure:

- geographic-area coverage;
- POI category 1 coverage;
- POI category 2 coverage;
- POI category 3 coverage; and
- population coverage.

Results are written to the city-level fields `spatialCoverage`, `spatialCoverageForPOI1`, `spatialCoverageForPOI2`, `spatialCoverageForPOI3`, and `spatialCoverageForPop` in `result.gpkg`.

### `spatialCoverage_Country`

```python
from analysis import spatialCoverage_Country

spatialCoverage_Country(CITIES, EVCS_GPKG, POI, POP, maxThread=8)
```

Performs the same coverage analysis at the country level using national boundaries. Results are written to the corresponding fields in the country-level result layer.

### `accessibilityRaster_Country`

```python
from raster import accessibilityRaster_Country

accessibilityRaster_Country(
    CITIES,
    EVCS_GPKG,
    POP,
    RESULTS_ROOT,
    maxThread=16,
)
```

Generates a country-level raster containing the distance from each valid population cell to its nearest public charging station.

Important parameters include `thres` (minimum EVCS count, default `10`), `blockSize`, and `maxThread`.

Output for each country:

```text
<RESULTS_ROOT>/accessibility/<ISO3>/<ISO3>.tif
```

Distance values are stored in meters. Countries below the threshold can receive a marker indicating insufficient EVCS observations.

### `accessibility_Country`

```python
from analysis import accessibility_Country

accessibility_Country(CITIES, POP, RESULTS_ROOT)
```

Combines each accessibility raster with the population rasters for total population, sex, age groups, and built-up/non-built-up populations. Population rasters are located automatically using the naming rules documented above.

Output:

```text
<RESULTS_ROOT>/accessibility/<ISO3>/<ISO3>_CountryLevel.csv
```

The CSV stores population totals by accessibility distance and supplies the accessibility plotting workflow.

### `gini_Country`

```python
from analysis import gini_Country

gini_Country(CITIES, POP_GLOBAL, EVCS_GPKG)
```

Evaluates country-level spatial equity between population and charging-infrastructure distributions using a Lorenz/Gini approach. It maps stations to population cells, constructs population-to-EVCS distributions, and writes `gini` to the country-level result layer.

Intermediate files are stored at:

```text
<RESULTS_ROOT>/lorenz/<ISO3>/<ISO3>_CountryLevel.csv
```

### `renewableEnergy`

```python
from analysis import renewableEnergy

renewableEnergy(CITIES, EVCS_GPKG)
```

Evaluates whether charging stations are located in relatively high renewable-resource areas within each city. For both the GHI and wind-speed rasters, the current implementation identifies the upper quartile and calculates the share of EVCS locations inside that high-potential area.

Required inputs:

```text
<RESULTS_ROOT>/GHI/GHI.tif
<RESULTS_ROOT>/wind_speed_cog_10m.tif
```

The derived city-level indicators are written as `solar_1` and `wind_1`.

### `exportCountryLevel`

```python
from analysis import exportCountryLevel

COUNTRIES_DATA = exportCountryLevel(CITIES, RESULTS_ROOT)
```

Creates a consolidated country-level reporting table. It combines country-level indicators with selected summaries of city-level results, including current median calculations for `spatialConcentration`, `solar_1`, and `wind_1`, and adds country names and regional classifications.

It returns a Pandas `DataFrame` and writes:

```text
<RESULTS_ROOT>/countrylevel.xlsx
```

---

## Plotting APIs

All plotting APIs write to `<FIG_ROOT>/fig_<language>/`.

### `plotCities`

```python
from plot import plotCities

LANGUAGE = "en"
plot = plotCities(CITIES, MAP_ELEMENT, FIG_ROOT, LANGUAGE)
```

Creates the principal city/regional mapping and statistical-figure interface. The constructor loads analysis results, level-1 and level-2 boundaries, major-city map elements, and special cartographic layers.

#### `plot.drawOverall()`

```python
plot.drawOverall()
```

Generates overall country-level report graphics, including ranking charts and heatmaps for POI-coverage indicators.

#### Dynamic metric methods

`plotCities` exposes metric-specific methods through a dynamic plotting interface. For example, `plot.spatialConcentration("CHN")` is equivalent to `plot.draw("spatialConcentration", "CHN")`.

| Method | Purpose |
|---|---|
| `plot.spatialConcentration(region)` | Maps and plots the city-level concentration indicator. |
| `plot.spatialCoverage(region)` | Maps city-level geographic EVCS coverage. |
| `plot.spatialCoverageForPop(region)` | Maps the population share covered by the EVCS buffer. |
| `plot.solar_1(region)` | Maps the derived city-level solar-potential indicator. |
| `plot.wind_1(region)` | Maps the derived city-level wind-potential indicator. |

Example:

```python
for region in ["CHN", "USA", "EUR"]:
    plot.spatialConcentration(region)
    plot.spatialCoverage(region)
    plot.spatialCoverageForPop(region)
    plot.solar_1(region)
    plot.wind_1(region)
```

### `plotAcccessibilityBar`

```python
from plot import plotAcccessibilityBar

ACCESSIBILITY_PLOT = plotAcccessibilityBar(
    RESULTS_ROOT,
    FIG_ROOT,
    language=LANGUAGE,
    tickSizeMultiple=1.5,
)

ACCESSIBILITY_PLOT.plotByCountry(countryLevel=True)
```

Reads the CSV files generated by `accessibility_Country()` and creates demographic accessibility bar charts. `plotByCountry()` groups distances into `≤ 1 km`, `1–2 km`, and `> 2 km`, then produces stacked percentage bars for total population, age groups, sex groups, and built-up/non-built-up populations.

Outputs are written under:

```text
<FIG_ROOT>/fig_<language>/accessibility/
```

### `newEnergy`

```python
from plot import newEnergy

NEW_ENERGY = newEnergy(CITIES, MAP_ELEMENT, FIG_ROOT, LANGUAGE)
NEW_ENERGY.draw("CHN")
NEW_ENERGY.draw("USA")
NEW_ENERGY.draw("EUR")
```

Creates maps of the **raw renewable-energy raster surfaces**. This differs from `plot.solar_1()` and `plot.wind_1()`, which map the derived city-level indicators stored in `result.gpkg`.

`newEnergy.draw()` reads the original GHI and wind-speed rasters, clips and reprojects them for the selected country or region, and produces files such as:

```text
<FIG_ROOT>/fig_<language>/<REGION>/map_solar_raw.jpg
<FIG_ROOT>/fig_<language>/<REGION>/map_solar_cbar.jpg
<FIG_ROOT>/fig_<language>/<REGION>/map_wind_raw.jpg
<FIG_ROOT>/fig_<language>/<REGION>/map_wind_cbar.jpg
```

---

## Example 2025 Workflow

```python
# Configuration
EVCS_GPKG = r"path\to\evcs.gpkg"
POI = r"path\to\poi.parquet"
POP = r"path\to\population"
POP_GLOBAL = r"path\to\global_population.tif"
BOUNDARY = r"path\to\boundary.gpkg"
BUILTUP = r"path\to\builtup.gpkg"
MAP_ELEMENT = r"path\to\map_elements.gdb"
RESULTS_ROOT = r"path\to\results"
FIG_ROOT = r"path\to\figures"
LANGUAGE = "en"

# Initialize analysis
from analysis import analysisByCities
CITIES = analysisByCities(RESULTS_ROOT, BOUNDARY, BUILTUP)

# EVCS raster
from raster import creatEVCS
creatEVCS(EVCS_GPKG, RESULTS_ROOT)

# Spatial concentration
from analysis import spatialConcentration
spatialConcentration(CITIES)

# Spatial coverage
from analysis import spatialCoverage, spatialCoverage_Country
spatialCoverage(CITIES, EVCS_GPKG, POI, POP, maxThread=8)
spatialCoverage_Country(CITIES, EVCS_GPKG, POI, POP, maxThread=8)

# Accessibility
from raster import accessibilityRaster_Country
from analysis import accessibility_Country
accessibilityRaster_Country(
    CITIES, EVCS_GPKG, POP, RESULTS_ROOT, maxThread=16
)
accessibility_Country(CITIES, POP, RESULTS_ROOT)

# Spatial equity
from analysis import gini_Country
gini_Country(CITIES, POP_GLOBAL, EVCS_GPKG)

# Renewable-energy potential
from analysis import renewableEnergy
renewableEnergy(CITIES, EVCS_GPKG)

# Country-level export
from analysis import exportCountryLevel
COUNTRIES_DATA = exportCountryLevel(CITIES, RESULTS_ROOT)

# City and regional figures
from plot import plotCities
plot = plotCities(CITIES, MAP_ELEMENT, FIG_ROOT, LANGUAGE)
plot.drawOverall()

for region in ["CHN", "USA", "EUR"]:
    plot.spatialConcentration(region)
    plot.spatialCoverage(region)
    plot.spatialCoverageForPop(region)
    plot.solar_1(region)
    plot.wind_1(region)

# Accessibility figures
from plot import plotAcccessibilityBar
plotAcccessibilityBar(
    RESULTS_ROOT,
    FIG_ROOT,
    language=LANGUAGE,
    tickSizeMultiple=1.5,
).plotByCountry(countryLevel=True)

# Raw renewable-energy maps
from plot import newEnergy
NEW_ENERGY = newEnergy(CITIES, MAP_ELEMENT, FIG_ROOT, LANGUAGE)

for region in ["CHN", "USA", "EUR"]:
    NEW_ENERGY.draw(region)
```

---

## Region Codes

| Code | Meaning |
|---|---|
| `CHN_ALL` | China, Hong Kong SAR, Macao SAR, and Taiwan |
| `CHN` | China map configuration used by the plotting workflow |
| `EUR` | European region defined by this project |
| `ASEAN` | ASEAN countries |
| `JPN&KOR` | Japan and South Korea |
| `USA&CAN` | United States and Canada |
| `AUS&NZL` | Australia and New Zealand |
| `GS` | Selected Global South countries |
| `Global` | Global study area |

---

## Output Summary

Analysis outputs are relative to `RESULTS_ROOT`:

```text
<RESULTS_ROOT>/
├── result.gpkg
├── evcs.tif
├── countrylevel.xlsx
├── accessibility/
│   └── <ISO3>/
│       ├── <ISO3>.tif
│       └── <ISO3>_CountryLevel.csv
└── lorenz/
    └── <ISO3>/
        └── <ISO3>_CountryLevel.csv
```

Figure outputs are relative to `FIG_ROOT` and separated by language:

```text
<FIG_ROOT>/
├── fig_en/
└── fig_zh/
```

---

## Important Notes

- `RESULTS_ROOT` is configurable and does not need to be named `data`.
- `FIG_ROOT` is independent from `RESULTS_ROOT`.
- Analysis outputs are written under `RESULTS_ROOT`.
- Figures are written under `FIG_ROOT/fig_en` or `FIG_ROOT/fig_zh`.
- `GHI/GHI.tif` and `wind_speed_cog_10m.tif` must be placed at their documented locations under `RESULTS_ROOT`.
- Population rasters must follow the required filename convention exactly.
- Population data used by the accessibility workflow must be in WGS84.
- CRS consistency is essential throughout the workflow.
- Several analyses use a default minimum threshold of 10 EV charging stations.
- The internal value `-100` identifies units that do not satisfy the minimum EVCS threshold in several outputs.
- Global and large-country raster operations can be computationally intensive.
- Increase `maxThread` where supported and appropriate for the available hardware.
- The repository is designed primarily as a research and annual-report workflow rather than a packaged general-purpose Python library.

---

## Research Context

The project evaluates EV charging infrastructure spatially rather than relying only on total station counts. It addresses questions such as:

- Where are charging stations concentrated?
- How much urban space is covered by charging infrastructure?
- How much population and urban activity is within convenient charging distance?
- How accessible are stations to different demographic groups?
- How equitably is infrastructure distributed relative to population?
- How well do station locations correspond to solar and wind resources?

The workflow is designed so the same analytical framework can be updated as new annual EVCS datasets become available.

---

## Contributing

Issues, suggestions, and contributions are welcome. Potential areas for improvement include:

- reproducibility;
- computational efficiency;
- large-scale raster processing;
- accessibility analysis;
- spatial-equity indicators;
- renewable-energy analysis;
- cartographic visualization;
- annual workflow automation; and
- documentation of input-data preprocessing.
