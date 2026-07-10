from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

from .language import languageTemplate

class baseTemplate(languageTemplate):
    __slots__ = ()

    # 3.1 Spatial Patterns
    sp = ("spatialConcentration", "spatialCoverage")
    # 3.2 Socioeconomic and Land-use Characteristics
    slc = ("spatialCoverageForPOI1", "spatialCoverageForPOI2", "spatialCoverageForPOI3", "spatialCoverageForPop")
    # 4.1 Charging Accessibility Assessment 
    acc = ("acc1km_percentage",)
    # 4.2 Charging Equity Assessment
    ginis = ("gini",)
    # 4.3 Renewable Energy Potential
    rep = ("solar_1", "wind_1")
    # Other
    slcGini = ("gini_poi1", "gini_poi2", "gini_poi3")

    groups = (sp, slc, acc, ginis, rep, slcGini)

    __COLS = {item for tup in groups for item in tup}

    __CLS_NAME = {
        "plotCities": ("cities map", "map"),
        "plotBar": ("cities bar", "chart")
    }
    
    def __getattr__(self, name: str):
        """
        Using column name such as nadrawSpatialConcentration directly to load self.__draw。
        """
        if name in self.__COLS:
            return lambda *args, **kwargs: self.draw(name, *args, **kwargs)
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def __dir__(self):
        base = set(super().__dir__())

        return sorted(base | self.__COLS)
    
    @property
    def cols(self) -> list[str]:
        return [item for tup in self.groups for item in tup]
    
    def drawAll(self, cols: list[str] = [], iso3s: list[str] = [], maxThread: int = 1) -> None:
        drawing = self.__CLS_NAME[self.__class__.__name__]
        cols = self.cols if cols == [] else cols
        iso3s = ["Global", "EUR", "USA", "CHN"] if iso3s == [] else iso3s
        bar = tqdm(total=len(cols)*len(iso3s), desc="Drawing {}".format(drawing[0]), unit=drawing[1])
        futures = []

        with ProcessPoolExecutor(max_workers=maxThread) as executor:
            for col in cols:
                for iso3 in iso3s:
                    futures.append(executor.submit(self.draw, col, iso3))

        for _ in as_completed(futures):
            bar.update(1)
        bar.close()
        
        return