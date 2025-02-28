import numpy as np
import pytest
from datetime import datetime

from util.parse import parse_datetime_location, consecutive_intervals, extract_integers


@pytest.fixture(scope="module", params=[
    "05.05.2000 13:37",
    "30.12.2025 23:59"
])
def timestamp(request):
    return datetime.strptime(request.param, "%d.%m.%Y %H:%M")


@pytest.fixture(scope="module", params=[
    "somewhere",
    "behind the moon",
    "double  space",
    "__underscore_"
])
def location(request):
    return request.param


@pytest.mark.parametrize("include_time", [True, False])
def test_parse_datetime_location(timestamp, location, include_time):
    string = timestamp.strftime("%Y-%m_%d" +
                                ("_%H%M" if include_time else "")
                                )
    string += "_"+location.replace(' ', "-")
    print(string)
    parsed_time, parsed_location = parse_datetime_location(string)

    if not include_time:
        assert parsed_time == timestamp.replace(hour=0, minute=0)
    else:
        assert parsed_time == timestamp
    assert parsed_location == location.replace("  ", " ").replace("_", "")


@pytest.mark.parametrize('ranges', [
    [(0, 20)],
    [(0, 3), (5, 9)],
    [(0, 3), (5, 9), (20, 22)],
    [(-5, 3), (10, 20)],
    [(0, 1861), (5941, 9999)],
])
def test_consecutive_intervals(ranges):
    list_of_ints = np.concatenate(
        [np.arange(r[0], r[1]+1, dtype=int) for r in ranges])

    result = consecutive_intervals(list_of_ints)

    assert len(result) == len(ranges)
    for idx, r in enumerate(ranges):
        interval = result[idx]
        assert interval[0] == r[0]
        assert interval[-1] == r[1]
        assert len(interval) == ((r[1]+1) - r[0])

def test_extract_integers():
    assert extract_integers("000") == [0]
    assert extract_integers("string34") == [34]
    assert extract_integers("my5string34") == [5,34]
    assert extract_integers("IMG_1230.tif") == [1230]
    
