from pathlib import Path
from typing import Union, List
from util.docker import mount, run_shell_command
import logging

logger = logging.getLogger(__name__)


def list_TIFFs_in_folder(folder: Path):
    return [file for file in folder.iterdir() if file.is_file() and file.suffix == '.tif']


def convert_raws(*raws_or_folder: Union[List[Path], Path], temp_folder: Path, cpuset_cpus: str = None, dry_run=False, force=0):

    if len(raws_or_folder) == 0:
        logger.warn(" No input files/folder given")
        return
    elif len(raws_or_folder) == 1:
        raw_folder = raws_or_folder[0]
        rt_input = raws_or_folder[0]
    else:
        rt_input = " ".join(raws_or_folder)
        raw_folder = Path(raws_or_folder[0]).parent

    profile = Path(__file__).parent / \
        "../data/neutral_denoising_CA_autolens.pp3"
    profile = profile.resolve()

    rt_command = [
        "rawtherapee-cli",
        "-t -b16",                 # 16bit-TIFF possible compression: -tz
        "-p " + str(profile),
        "-o " + str(temp_folder),  # output folder
        "-Y" if force >= 3 else "",
        "-c " + str(rt_input),   # input folder
    ]
    logger.debug(f" RawTherapee command {' '.join(rt_command)}")
    task_id = hash(" ".join(rt_command))

    docker_command = [
        "docker",
        "run --rm -it",
        # "-p 127.0.0.1:5901:5901",
        # "-u $(id -u):$(id -g)",
        f"--cpuset-cpus=\"{cpuset_cpus}\"" if cpuset_cpus else "",
        mount(Path("/projects")),
        mount(profile),
        mount(raw_folder),
        mount(temp_folder, write=True),
        "--name skygan-data_rawtherapee"+str(task_id),
        "docker-gui-reg"
    ]
    logger.debug(f" Docker command {' '.join(docker_command)}")

    if not dry_run:
        run_shell_command(" ".join(docker_command + rt_command), shell=True)
        return list_TIFFs_in_folder(temp_folder)
    else:
        return []
