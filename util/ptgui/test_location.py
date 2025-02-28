import pytest
from .location import *

def test_location():
    lat, long, dir = (4, 6, 7)
    loc = Location(latitude=lat, longitude=long, direction=dir)
    contents = dict(**loc)
    assert list(contents.keys()) == ["overridelatitude", "overridelongitude", "overridedirection"]
    assert contents["overridelatitude"] == lat
    assert contents["overridelongitude"] == long
    assert contents["overridedirection"] == dir
