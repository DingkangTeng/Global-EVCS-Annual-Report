from typing import Literal

from __plot import plt

class languageTemplate:
    __slots__ = ["language"]

    # Language denfination
    __LANGUAGE = ["zh", "en"]
    LANGUAGE = Literal["zh", "en"]

    def __init__(self, language: LANGUAGE, tickSizeMultiple: float = 0) -> None:
        if language not in self.__LANGUAGE:
            raise ValueError(f"language must be one of {self.__LANGUAGE}, got {language}")
        plt.setLanguage(language)
        self.language = language

        if tickSizeMultiple != 0:
                plt.plt.rcParams["font.size"] *= tickSizeMultiple
                plt.plt.rcParams["xtick.labelsize"] *= tickSizeMultiple
                plt.plt.rcParams["ytick.labelsize"] *= tickSizeMultiple
                plt.plt.rcParams["axes.labelsize"] *= tickSizeMultiple
        
        return