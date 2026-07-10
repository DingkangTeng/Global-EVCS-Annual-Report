from . import plt
from .__setting import NOTE_SIZE, TICK_SIZE, LABEL_SIZE, BOX_KWARGS

# Color map
BAR_COLORS = [
    ["#2F7FC1", "#54B345", "#F3D266", "#D8383A"],
    ["#436C85", "#B73F42", "#DE9960", "#82B29B", "#EEE6CB"],
    ["#DE476A", "#76AEA6", "#D79E8F", "#E5D2C4", "#F0E0D3"],
    ["#7D5A8A", "#DE7294", "#90BBAA", "#E6D2C2", "#F0E0D3"],
    ["#165188", "#BFCF61", "#9FCBC3", "#BFD3BC", "#DDDAB4"],
]

def BAR_COLORS_TRANS(alpha: float = 0.5, group: int | None = 0) -> list:
    from matplotlib.colors import to_rgba
    
    if group is None:
        return [[to_rgba(color, alpha) for color in colors] for colors in BAR_COLORS]
    
    else:
        return [to_rgba(color, alpha) for color in BAR_COLORS[group]]

# General setting
def plotSet(scal1: float | int = 1, scal2: float | int = 1) -> None:
    import matplotlib.pyplot as plt
    from .__setting import LABEL_SIZE, TICK_SIZE
    
    labelSize = int(LABEL_SIZE * scal1)
    tickSize = int(TICK_SIZE * scal2)
    plt.style.use("seaborn-v0_8-whitegrid")
    # Font setting
    plt.rcParams["font.sans-serif"] = "Times New Roman" # "Sans Serif Collection"
    plt.rcParams["font.size"] = tickSize
    plt.rcParams["xtick.labelsize"] = tickSize
    plt.rcParams["ytick.labelsize"] = tickSize
    plt.rcParams["axes.labelsize"] = labelSize
    # legend format
    plt.rcParams["legend.facecolor"] = "white"
    plt.rcParams["legend.edgecolor"] = "lightgray"
    plt.rcParams['legend.frameon'] = True
    plt.rcParams["legend.framealpha"] = 1.0
    # axes setting
    plt.rcParams["axes.formatter.use_mathtext"] = False
    plt.rcParams["axes.labelweight"] = "bold"
    # save setting
    plt.rcParams["savefig.dpi"] = 300

    return

# Run set directly
plotSet()