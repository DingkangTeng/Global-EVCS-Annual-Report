import numpy as np

def __calIndex(raster: np.ndarray, mainData: bool = True) -> float:
    if mainData or (not mainData and len(raster) > 1):
        raster = np.sort(raster)
        top = raster[-int(np.ceil(len(raster) * 0.1)):]
    
        return np.sum(top) / np.sum(raster)
    
    elif not mainData and len(raster) == 1:
        return 1
    
    else:
        return -100