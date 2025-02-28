from pathlib import Path
from typing import Union, List, Dict
import copy
import logging
import json
import tempfile

from util.docker import mount, run_shell_command
from util.exif import get_img_metadata
from .projection import Projection, get_projection
from .location import Location

logger = logging.getLogger(__name__)


def output_exists(prefix: Path):
    hdr = Path(str(prefix) + '_hdr.exr')
    ldr = prefix.with_suffix('.jpg')
    return hdr.exists() and ldr.exists()


def set_location(data: Dict, location: Location):
    data["project"]["metadata"].update(location)


def set_projection(data: Dict, projection: Projection):
    data["project"]["panoramaparams"]["projection"] = str(projection)
    data["project"]["panoramaparams"].update(projection.panoramaparams())


def set_resolution(data: Dict,
                   resolution_or_percent: Union[int, float],
                   projection: Projection):
    if type(resolution_or_percent) == int:
        params = projection.panoramaparams()
        aspect_ratio = params["hfov"] / params["vfov"]
        if aspect_ratio >= 1.0:
            width = resolution_or_percent
            height = width / aspect_ratio
        else:
            height = resolution_or_percent
            width = height * aspect_ratio
        outputsize = {
            "mode": "fixed",
            "pixels": width * height,
        }
        logger.debug(f"Setting resolution to {width}x{height}")
    elif type(resolution_or_percent) == float:
        assert 0 < resolution_or_percent and resolution_or_percent <= 100.0
        outputsize = {
            "mode": "fixed",
            "fractionofoptimumsize": resolution_or_percent,
        }
        logger.debug(
            f"Setting resolution at {resolution_or_percent}% of optimum size")

    data["project"]["outputsize"] = outputsize


def set_sensor_lens(data, camera_str, lens_str):
    lens = data["project"]["globallenses"][0]["lens"]
    if "Canon EOS 6D Mark II" in camera_str:
        lens["params"].update(
            sensordiagonal=43.1834459023359969,
            cropcircleradius=1.15850675494012236e1,
            cropcenteroffset={
                "longside": -1.01942052881792027e-3,
                "shortside": -5.77909240148094701e-3
            },
        )
    elif "Canon EOS 5D Mark II" in camera_str:
        lens["params"].update(
            sensordiagonal=43.2666153055680027,
            cropcircleradius=1.15850675494012236e1,
            cropcenteroffset={
                "longside": -1.87548245040657828e-3,
                "shortside": 1.87228362718857993e-8
            },
        )
    else:
        raise RuntimeError(
            f"Unknown camera {camera_str}. Please calibrate and update the code")

    if "EF8-15mm f/4L FISHEYE USM" in lens_str:
        lens["params"].update(
            projection="circularfisheye",
            fisheyefactor=-5.05769000000000024e-1,
            focallength=8.21231655320238829,
        )
    else:
        raise RuntimeError(
            f"Unknown lens {lens_str}. Please calibrate and update the code")


def insert_images(data: Dict,
                  list_of_tiffs: List[Path],
                  output_file: Path,
                  projection: Projection,
                  exposure_shift_EV100: float):
    img_group = data["project"]["imagegroups"][0]

    template_image = img_group["images"][0]
    img_group["images"] = []
    size = ()
    camera_lens = None

    for tiff in list_of_tiffs:
        img = copy.deepcopy(template_image)
        img["filename"] = str(tiff.relative_to(output_file.parent))

        metadata = get_img_metadata(tiff)
        img["metadata"]["aperture"] = metadata["aperture"]
        img["metadata"]["exposuretime"] = metadata["exposuretime"]
        img["metadata"]["iso"] = metadata["iso"]

        filestats = tiff.stat()
        img["metadata"]["filesize"] = filestats.st_size
        img["metadata"]["filetimestamp"] = int(filestats.st_ctime)

        img["photometric"]["exposureoffset"] = exposure_shift_EV100

        if len(size) == 0:
            size = (metadata["width"], metadata["height"])
        else:
            assert size[0] == metadata["width"] and size[1] == metadata["height"]

        if not camera_lens:
            camera_lens = metadata["camera"], metadata["lens"]
        else:
            assert camera_lens[0] == metadata["camera"], "Images not taken with the same camera"
            assert camera_lens[1] == metadata["lens"], "Images not taken with the same lens"

        img_group["images"].append(img)

    img_group["size"] = size

    img_group["position"]["params"].update(projection.rotation())
    img_group["linkable"]["position"]["params"].update(projection.rotation())

    set_sensor_lens(data, *camera_lens)


def gen_ptgui_project(list_of_tiffs: List[Path],
                      output_file: Path,
                      projection="equirectangular",
                      resolution_or_percent: Union[int, float] = 100.0,
                      location: Location = Location(),
                      exposure_shift_EV100: float = 0.0,
                      dry_run=False, force=0):
    template = Path(__file__).parent / \
        "../../data/fisheye_up_template.pts"
    template = template.resolve()
    projection_ = get_projection(projection)

    logger.debug(f" Generating {output_file} from {template}")

    with open(template) as f:
        data = json.load(f)

    set_location(data, location)
    set_projection(data, projection_)
    set_resolution(data, resolution_or_percent, projection_)
    insert_images(data, list_of_tiffs=list_of_tiffs,
                  output_file=output_file, projection=projection_,
                  exposure_shift_EV100=exposure_shift_EV100)

    if (not dry_run) and ((not output_file.exists()) or force >= 1):
        logger.debug(f" Writing PTGui JSON project {output_file}")
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)


def stitch_project(projects: Union[List[Path], Path], cpuset_cpus: str = None, dry_run=False, force=0):
    if type(projects) != list:
        projects = [projects]

    ptgui_command = [
        "/ptgui/PTGui",
        "-stitchnogui"
    ]
    ptgui_command.extend([str(prj) for prj in projects])

    mounts = set()
    for project in projects:
        mount_project = str(project.parent)
        mounts.add(mount_project)

    logger.debug(f" PTGui command {' '.join(ptgui_command)}")
    task_id = hash(" ".join(ptgui_command))

    encoding = 'ascii'
    xstartup = tempfile.NamedTemporaryFile(
        'w+', encoding=encoding, delete=False)
    xstartup.write(" ".join(ptgui_command))
    xstartup.flush()
    xstartup.close()
    Path(xstartup.name).chmod(0o755)

    docker_command = [
        "docker",
        "run --rm -it",
        # "-p 127.0.0.1:5901:5901",
        # "-u $(id -u):$(id -g)",
        f"--cpuset-cpus=\"{cpuset_cpus}\"" if cpuset_cpus else "",
        mount(Path("/projects")),
        f"-v {xstartup.name}:/root/.vnc/xstartup:ro",
        *[mount(m, write=True) for m in mounts],
        "--name skygan-data_ptgui"+str(task_id),
        "docker-gui-reg"
    ]
    logger.debug(f" Docker command {' '.join(docker_command)}")

    if not dry_run:
        run_shell_command(
            " ".join(docker_command), shell=True)

    Path(xstartup.name).unlink()
