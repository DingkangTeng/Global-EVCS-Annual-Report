import numpy as np

from __plot import plt, BAR_COLORS

def _gini(
    indicator: np.ndarray, evcs:np.ndarray,
    savePath: str, city: str, sorted: bool = True
) -> float:
    # Special case: if only one grid cell has nonzero indicatior
    # Return nan if total count less than 10, because no significant meaning for gini
    if np.count_nonzero(evcs) <= 10: return -100

    # Sort values by EVCS in ascending order
    if not sorted:
        # Reserved API for unsorted data
        raise RuntimeError()
    else:
        sortedIndicator = indicator
        sortedEVCS = evcs

    # Compute cumulative EVCS and cumulative indicatior
    totalIndicator = sortedIndicator.sum()
    if totalIndicator == 0: return 0
    totalEVCS = sortedEVCS.sum()

    # Normalize cumulative EVCS and indicatior (range 0–1)
    cumIndicator = np.cumsum(sortedIndicator) / totalIndicator
    cumEVCS = np.cumsum(sortedEVCS) / totalEVCS
    ## Add 0
    lack0 = cumIndicator[0] != 0 or cumEVCS[0] != 0
    cumIndicator = np.insert(cumIndicator, 0, 0) if lack0 else cumIndicator 
    cumEVCS = np.insert(cumEVCS, 0, 0) if lack0 else cumEVCS
    gini = np.float64(1 - 2 * np.trapezoid(cumEVCS, cumIndicator))

    # Plot lorenz curve
    _, ax = plt.figure("D")
    ax.plot(
        cumIndicator, cumEVCS,
        label="Lorenz curve",
        color=BAR_COLORS[0][1]
    )
    ax.plot([0, 1], [0, 1], label="Equality line", linestyle="--", color="gray")
    ax.set_title(f"{gini:.4f}")
    plt.xlabel("Cumulative share of population")
    plt.ylabel("Cumulative share of EVCS")
    plt.plot(savePath, "{}.jpg".format(city), bbox_inches="tight")

    # Compute the Gini coefficient using the trapezoidal rule (Lorenz curve area)
    return gini