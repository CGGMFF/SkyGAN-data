
class Location(dict):
    def __init__(self,
                 latitude: float = 0.0,
                 longitude: float = 0.0,
                 direction: float = 0.0):
        self["overridelatitude"] = latitude
        self["overridelongitude"] = longitude
        self["overridedirection"] = direction