from pathlib import Path
from typing import Union, List
from util.docker import mount, run_shell_command
import logging

logger = logging.getLogger(__name__)


def generate_video_preview(video_filename: Path, preview_filename: str, cpuset_cpus: str = None, dry_run=False, force=0):
    overwrite = force >= 2
    verbosity = "warning" if logger.getEffectiveLevel() >= 20 else "info"

    ffmpeg_command = [
        "-y" if overwrite else "-n",
        f"-v {verbosity}",
        f"-i {video_filename.name}.mp4",
        "-vf \"select='eq(pict_type,PICT_TYPE_I)',yadif,scale=512:-1,tile=2x2\"",
        "-frames:v 1",
        "-q:v 2",
        f"{preview_filename}.jpg"
    ]
    logger.debug(f" FFmpeg command ffmpeg {' '.join(ffmpeg_command)}")
    task_id = hash(" ".join(ffmpeg_command))

    folder = video_filename.parent

    docker_command = [
        "docker",
        "run --rm -it",
        # "-u $(id -u):$(id -g)",
        f"--cpuset-cpus=\"{cpuset_cpus}\"" if cpuset_cpus else "",
        mount(folder, write=True),
        f"-w {folder}",
        "-v /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf:/font.ttf",
        "--name skygan-data_ffmpeg"+str(task_id),
        "jrottenberg/ffmpeg:4.4-scratch"
    ]
    logger.debug(f" Docker command {' '.join(docker_command)}")

    if not dry_run and (overwrite or not (folder/(preview_filename+'.jpg')).exists()):
        run_shell_command(
            " ".join(docker_command + ffmpeg_command), shell=True)


def generate_video(folder: Path, frames_glob_pattern: str, video_filename: str, cpuset_cpus: str = None, dry_run=False, force=0):
    overwrite = force >= 2
    verbosity = "warning" if logger.getEffectiveLevel() >= 20 else "info"

    ffmpeg_command = [
        "-y" if overwrite else "-n",
        f"-v {verbosity}",
        "-f image2",
        "-pattern_type glob",
        "-framerate 15",
        "-export_path_metadata 1",
        "-apply_trc iec61966_2_1" if ("exr" in frames_glob_pattern) else "",
        f"-i {frames_glob_pattern}",
        "-c:v libx264 -crf 28 -pix_fmt yuv420p",
        "-preset superfast",  # veryslow
        "-filter_complex:v \""
        "[0] exposure=exposure=-3,scale=160:160,format=pix_fmts=gbrapf32le,drawtext=fontfile=/font.ttf:text='-3':fontcolor=white:x=4:y=main_h-text_h-4 [lower]; "
        "[0] exposure=exposure=+3,scale=160:160,format=pix_fmts=gbrapf32le,drawtext=fontfile=/font.ttf:text='+3':fontcolor=white:x=main_w-text_w-4:y=main_h-text_h-4 [upper]; "
        "[0] format=pix_fmts=yuv444p12le, histogram=display_mode=overlay:levels_mode=logarithmic:level_height=300:components=1:fgopacity=1.0,scale=150:150 [hist]; "
        "[0][lower] overlay=x=0:y=main_h-overlay_h:eval=init:format=yuv420 [main_lower]; "
        "[main_lower][upper] overlay=x=main_w-overlay_w:y=main_h-overlay_h:eval=init:format=yuv420 [main_lower_upper]; "
        "[main_lower_upper][hist] overlay=x=main_w-overlay_w:y=0:eval=init:format=yuv420 [main_lower_upper_hist]; "
        "[main_lower_upper_hist] drawtext=fontfile=/font.ttf:x=8:y=8:text='%{metadata\\:lavf.image2dec.source_path}':fontcolor=white"
        "\"",  # end filter graph
        f"{video_filename}.mp4"
    ]
    logger.debug(f" FFmpeg command ffmpeg {' '.join(ffmpeg_command)}")
    task_id = hash(" ".join(ffmpeg_command))

    docker_command = [
        "docker",
        "run --rm -it",
        # "-u $(id -u):$(id -g)",
        f"--cpuset-cpus=\"{cpuset_cpus}\"" if cpuset_cpus else "",
        mount(folder, write=True),
        f"-w {folder}",
        "-v /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf:/font.ttf",
        "--name skygan-data_ffmpeg"+str(task_id),
        "jrottenberg/ffmpeg:4.4-scratch"
    ]
    logger.debug(f" Docker command {' '.join(docker_command)}")

    if not dry_run and (overwrite or not (folder/(video_filename+'.mp4')).exists()):
        run_shell_command(
            " ".join(docker_command + ffmpeg_command), shell=True)
