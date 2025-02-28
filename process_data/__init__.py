from util.exif import get_exposure_shift, read_timestamps_from_folder, group_timestamps_by_seconds
from util.ffmpeg import generate_video, generate_video_preview
from util.parse import parse_datetime_location
from util.ptgui import gen_ptgui_project, stitch_project, output_exists, Location
from util.rawtherapee import convert_raws
from util.qmc import halton_sequence
import os
import shutil
import tqdm
from pathlib import Path
import logging
logger = logging.getLogger(__name__)


class DataProcessor():
    def __init__(self,
                 outdir: Path,
                 dry_run: bool,
                 force: int,
                 limit_img: int,
                 cpuset_cpus: str
                 ):
        self.outdir = Path(outdir)
        self.dry_run = bool(dry_run)
        self.force = int(force)
        self.limit_img = int(limit_img)
        self.cpuset_cpus = cpuset_cpus

        tmpfs = os.environ.get("XDG_RUNTIME_DIR", None)
        if tmpfs:
            self.workdir = Path(tmpfs)
        else:
            self.workdir = self.outdir
        logger.info(
            f"Using {self.workdir} as an intermediate processing directory")

        if not self.dry_run:
            self.outdir.mkdir(parents=True, exist_ok=True)

        self.duplicate_set = {}

    @property
    def inplace(self):
        return self.workdir == self.outdir

    @property
    def cleanup(self):
        return (not self.dry_run) and (not self.inplace)

    def __del__(self):
        if len(self.duplicate_set):
            import pprint
            pp = pprint.PrettyPrinter()
            logger.warn(f"{len(self.duplicate_set)} duplicate items found + skipped\n"
                        f"{pp.pformat(self.duplicate_set)}")

    def process_folders(self, folder: Path):
        logger.info(f"Processing input {folder}")

        assert folder != self.outdir, "In-place operations not permitted"

        children = [f for f in folder.iterdir() if f.is_dir()]
        children = sorted(children, reverse=False)
        for subfolder in tqdm.tqdm(children,
                                   desc="Processing folders",
                                   disable=logger.getEffectiveLevel() >= 20):
            if subfolder.is_file():
                continue
            self.process_folder(subfolder, is_sub_call=True)

    def process_folder(self, subfolder: Path, is_sub_call=False):
        assert subfolder != self.outdir, "In-place operations not permitted"

        if not is_sub_call:
            logger.info(f"Processing input {subfolder}")
        else:
            logger.info("="*60)
            logger.info(f"Reading {subfolder}")

        timestamp, location_str = parse_datetime_location(subfolder.name)
        logger.debug(f" Captured on {timestamp} @ {location_str}")

        # consistent output formatting
        # YEAR_MONTH_DAY_HOURMIN_LOCATION_WITH_UNDERSCORE
        output_id = (timestamp.strftime("%Y_%m_%d_%H%M_") +
                     location_str.replace(" ", "_"))
        out = self.outdir / output_id
        processing_folder = self.workdir / output_id
        logger.debug(
            f" {'Potential o' if self.dry_run else 'O'}utput dir {out}")
        if out.exists() and self.force == 0:
            count = self.duplicate_set.get(output_id, 0)
            self.duplicate_set[output_id] = count + 1
            logger.debug(" Skipping")
            return

        if not self.dry_run:
            out.mkdir(exist_ok=True)
            processing_folder.mkdir(exist_ok=True)

        location = Location()

        # Group
        try:
            dataframe = read_timestamps_from_folder(subfolder)
            groups = group_timestamps_by_seconds(dataframe)
        except Warning as e:
            logger.error(e)
            # TODO cleanup directory
            return

        # Detect exposure shift from one image stack in the middle of the shooting session
        keys = list(groups.indices.keys())
        middle = keys[len(keys) // 2]
        exposure_shift = get_exposure_shift(
            groups.get_group(middle)["filenames"])
        logger.info(
            f"The shooting has {len(groups.get_group(middle))} exposures with a shift of {exposure_shift:.2} EV100")

        # Limit number of processed images per folder
        if self.limit_img > 0:
            limited_groups = []
            for n, idx in enumerate(halton_sequence(self.limit_img, base=2)):
                g_key = keys[int(len(keys) * idx)]
                limited_groups.append((n, groups.get_group(g_key)))
            groups = limited_groups

        for idx, group in tqdm.tqdm(groups, leave=not is_sub_call, desc="Processing image stacks"):
            start_time = group.reset_index(
            ).iloc[0]["timestamp"].strftime("%H_%M_%S")
            stack_folder = processing_folder / start_time

            destination_ll = out / start_time / (start_time + "_ll")
            destination_sup = out / start_time / (start_time + "_sup")
            if output_exists(destination_ll) and output_exists(destination_sup) and (not self.force >= 2):
                logger.debug(
                    f' Image already exists {start_time}, skipping. Apply -ff to overwrite it.')
                continue

            if not self.dry_run:
                stack_folder.mkdir(exist_ok=True)

            # Convert RAWs to 16-bit TIFF using rawtherapee
            # Performs denoising, debayering, CA correction
            tiffs = convert_raws(*group["filenames"],
                                 temp_folder=stack_folder,
                                 cpuset_cpus=self.cpuset_cpus,
                                 dry_run=self.dry_run,
                                 force=self.force)

            project_ll = stack_folder / (start_time + "_ll.pts")
            gen_ptgui_project(tiffs, project_ll,
                              projection="equirectangular",
                              resolution_or_percent=8192,
                              location=location,
                              exposure_shift_EV100=exposure_shift,
                              dry_run=self.dry_run, force=self.force)

            project_sup = stack_folder / (start_time + "_sup.pts")
            gen_ptgui_project(tiffs, project_sup,
                              projection="stereographic",
                              resolution_or_percent=1024,
                              location=location,
                              exposure_shift_EV100=exposure_shift,
                              dry_run=self.dry_run, force=self.force)

            stitch_project([project_ll, project_sup], cpuset_cpus=self.cpuset_cpus,
                           dry_run=self.dry_run, force=self.force)

            if self.cleanup:
                shutil.copytree(processing_folder,
                                out,
                                ignore=shutil.ignore_patterns(
                                    "*.tif", "*.pts"),
                                dirs_exist_ok=True)
                shutil.rmtree(stack_folder)

        if self.cleanup:
            shutil.rmtree(processing_folder)

        generate_video(out, "*/*_sup_hdr.exr", "preview_sup",
                       cpuset_cpus=self.cpuset_cpus,
                       dry_run=self.dry_run, force=self.force)
        generate_video_preview(out/"preview_sup", "preview_sup",
                       cpuset_cpus=self.cpuset_cpus,
                       dry_run=self.dry_run, force=self.force)
