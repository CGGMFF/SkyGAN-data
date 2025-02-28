import pytest
from .projection import *

def test_get_projection():
    eq = get_projection("equirectangular")
    assert type(eq) == Equirectangular
    assert_projection(eq)

    sg = get_projection("stereographic")
    assert type(sg) == Stereographic
    assert_projection(sg)

def assert_projection(projection: Projection):
    assert str(projection) == type(projection).__name__.lower()

    panoparams = projection.panoramaparams()
    assert type(panoparams) == dict
    assert list(panoparams.keys()) == ["hfov", "vfov"]

    rotation = projection.rotation()
    assert type(rotation) == dict
    assert list(rotation.keys()) == ["yaw", "pitch", "roll"]