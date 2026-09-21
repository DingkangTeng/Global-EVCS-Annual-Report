from dataclasses import dataclass
from typing import TypedDict

# Fig size
LABEL_SIZE = 28
TICK_SIZE = int(LABEL_SIZE * 0.9)
NOTE_SIZE = int(LABEL_SIZE * 0.7)
@dataclass(frozen=True)
class __FIG_SIZE:
    D: tuple[int, int] = (13, 12)   # Default
    W: tuple[int, int] = (26, 12)   # Wide
    SLIM: tuple[int, int] = (12, 20)
    BIG: tuple[int, int] = (38, 45)
    # Special
    HorBar: tuple[int, int] = (7, 1)
FIG_SIZE = __FIG_SIZE()

# Boxplot color kwgs
class __BoxplotKwargs(TypedDict):
    medianprops: dict[str, str]
    whiskerprops: dict[str, str]
    capprops: dict[str, str]
    meanprops: dict[str, str]

BOX_KWARGS: __BoxplotKwargs = {
    "medianprops": {"color": "white"},
    "whiskerprops": {"color": "gray"},
    "capprops": {"color": "gray"},
    "meanprops": {"markerfacecolor": "lightgreen"},
}