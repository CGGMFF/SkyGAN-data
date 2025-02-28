from .parse import consecutive_intervals, extract_integers
from typing import List
from pathlib import Path
from tqdm import tqdm
import exifread
import pandas as pd
import numpy as np
import datetime
import logging
logger = logging.getLogger(__name__)


def correct_wraparound_image_sorting(paths: List[Path]):
    numbers = [extract_integers(p.name)[0] for p in paths]
    intervals = consecutive_intervals(numbers)
    if len(intervals) == 2:
        boundary = len(intervals[0])
        first_segment = paths[:boundary]
        paths = paths[boundary:]
        paths.extend(first_segment)
    elif len(intervals) > 2:
        logger.warning(
            "Found non-consecutively named images, "
            "which could hint at missing images in the shooting.")
        logger.debug(f"Found intervals {intervals}")
    return paths


def get_img_timestamp(filepath: Path):
    with open(filepath, 'rb') as file:
        img = exifread.process_file(file, stop_tag='DateTime', details=False)
        return str(img["Image DateTime"])


def get_img_metadata(filepath: Path):
    with open(filepath, 'rb') as file:
        exif = exifread.process_file(file, details=True)
        data = {
            'width': int(str(exif["Image ImageWidth"])),
            'height': int(str(exif["Image ImageLength"])),
            'exposuretime': float(eval(str(exif["EXIF ExposureTime"]))),
            'aperture': float(eval(str(exif["EXIF FNumber"]))),
            'iso': float(str(exif["EXIF ISOSpeedRatings"])),
            'camera': str(exif["Image Model"]),
            'lens': str(exif.get("EXIF LensModel", exif["MakerNote LensModel"])),
        }
    data["EV100"] = np.log2(
        ((data['iso'] / 100) * data['aperture'] ** 2) / data["exposuretime"])
    return data


def get_exposure_shift(list_of_imgs: List[Path], reference_middle_EV100=14):
    imgs_metadata = [get_img_metadata(img) for img in list_of_imgs]
    EVs = [m["EV100"] for m in imgs_metadata]
    logger.debug(f"EV values are {EVs}")
    logger.debug(f"Metadata values are {list(zip(list_of_imgs, imgs_metadata))}")
    return np.median(EVs) - reference_middle_EV100


def str_to_pd_timestamp(x: str):
    return pd.Timestamp(datetime.datetime.strptime(x, "%Y:%m:%d %H:%M:%S"))


def read_timestamps_from_folder(folder: Path, limit: int = -1):
    cache_filename = folder / "exif.csv"
    if cache_filename.exists():
        return pd.read_csv(cache_filename,
                           index_col="timestamp",
                           parse_dates=True
                           ).sort_index()

    children = sorted([file for file in folder.iterdir() if file.is_file()])
    if len(children) == 0:
        logger.error(f"Skipping empty directory {folder}.")
        raise RuntimeWarning("Empty directory found")
    children = correct_wraparound_image_sorting(children)

    if limit < 0:
        limit = len(children)

    filenames = []
    timestamps = []
    for file in tqdm(children[:limit], leave=False, desc="Reading EXIF timestamps"):
        try:
            timestamps.append(str_to_pd_timestamp(get_img_timestamp(file)))
            filenames.append(str(file.absolute()))
        except KeyError:
            logger.warning(f"Could not read timestamp from {file}")

    df = pd.DataFrame({"filenames": filenames,
                       "timestamp": timestamps}).set_index("timestamp").sort_index()
    df.to_csv(cache_filename)
    return df


def group_timestamps_by_seconds(df):
    timediff = df.reset_index("timestamp")["timestamp"].diff()
    threshold = timediff.quantile(0.9) * 0.8
    threshold_indices = timediff.index[timediff > threshold].to_series()
    threshold_indices = pd.concat([pd.Series([0]), threshold_indices])

    # ignore NaT and first one
    t_interval = timediff[threshold_indices.iloc[2:]]
    t_interval_low, t_interval_high = t_interval.min(), t_interval.max()
    if (t_interval_high - t_interval_low).seconds > 3:
        logger.warning(f"We are potentially missing images. "
                       f"There is a maximum time-interval of {t_interval_high} "
                       f"and a minimum time-interval of {t_interval_low}.")
        logger.debug(f"Time intervals: {t_interval}")

    intervals = threshold_indices.diff().iloc[1:].astype(int)
    if not np.allclose(intervals.std(), 0):
        logger.warning("Potentially irregular spacing across the timeline")
        with pd.option_context('display.min_rows', 50):
            logger.debug(f"{timediff}")
            logger.debug(f"{intervals}")
    images_per_series = intervals.median().astype(int)
    assert (5 <= images_per_series and images_per_series <=
            9), f"The number of images per HDR stack is usually between 5 and 9, got {images_per_series}"
    start_idx = threshold_indices.iloc[0] % images_per_series

    indices = np.arange(start_idx, len(df), images_per_series)
    group_indices = np.repeat(indices, images_per_series)[:len(df)]
    df["group_idx"] = group_indices

    groups = df.groupby("group_idx").filter(
        lambda g: len(g) == images_per_series)

    return groups.groupby("group_idx")
