import re
import datetime
import numpy as np
from typing import List


def consecutive_intervals(data, stepsize=1):
    return np.split(data, np.where(np.diff(data) != stepsize)[0]+1)


def try_parse_int(string, default):
    try:
        return int(string)
    except ValueError:
        return default


def parse_datetime_location(input_string):
    delimiters = ("-", "_")
    regex_pattern = '|'.join(map(re.escape, delimiters))
    components = re.split(regex_pattern, input_string)
    components = list(filter(None, components))

    parsed_time = {
        "year": int(components[0]),
        "month": int(components[1]),
        "day": int(components[2]),
        "hour": try_parse_int(components[3][:2], 0),
        "minute": try_parse_int(components[3][2:], 0),
    }

    doesnt_contain_time = (parsed_time["hour"] == 0 and
                           parsed_time["minute"] == 0)

    timestamp = datetime.datetime(**parsed_time)
    loc_split = 3 if doesnt_contain_time else 4
    location_str = " ".join(components[loc_split:])
    return timestamp, location_str


def extract_integers(input_string: str) -> List[int]:
    regex = re.compile(r'\d+')
    return [int(x) for x in regex.findall(input_string)]
