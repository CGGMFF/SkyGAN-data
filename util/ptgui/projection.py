from abc import ABC, abstractmethod
import sys
import inspect

class Projection(ABC):
    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def panoramaparams(self):
        pass

    @abstractmethod
    def rotation(self):
        pass


class Equirectangular(Projection):
    def __str__(self):
        return "equirectangular"

    def panoramaparams(self):
        return {
            "hfov": 360.0,
            "vfov": 180.0
        }

    def rotation(self):
        return {
            "yaw": -180.0,
            "pitch": 90.0,
            "roll": 0.0,
        }


class Stereographic(Projection):
    def __str__(self):
        return "stereographic"

    def panoramaparams(self):
        return {
            "hfov": 180.0,
            "vfov": 180.0
        }

    def rotation(self):
        return {
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
        }


def get_projection(key: str):
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    for name, Cls in clsmembers:
        if name.lower() == key:
            return Cls()
    raise RuntimeError(f"Unknown Projection \"{key}\"")
