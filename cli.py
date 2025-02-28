from process_data import DataProcessor
from util.log import Whitelist
from util import get_username

import click
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

for handler in logging.root.handlers:
    handler.addFilter(Whitelist(__name__, 'process_data', 'util'))

folder_arg = click.argument("folder", type=click.Path(exists=True,
                                                      file_okay=False,
                                                      resolve_path=True,
                                                      path_type=Path)
                            )
outdir_arg = click.option("--outdir", type=click.Path(exists=False,
                                                      file_okay=False,
                                                      resolve_path=True,
                                                      path_type=Path),
                          default=Path(f"/local/{get_username()}/")
                          )
dry_run_arg = click.option("--dry-run", "-n", type=bool, default=False,
                           is_flag=True,
                           help="Simulated processing, no changes to files"
                           )
overwrite_arg = click.option("--force", "-f", "--overwrite", count=True,
                             default=0,
                             help="Apply force: overwrite anything existing, can be applied twice"
                             )
verbose_arg = click.option("--verbose", "-v", count=True,
                           default=0,
                           help="Increase verbosity of logging output, can be applied twice"
                           )
num_img_arg = click.option("--limit-img", "-l", type=int, default=0,
                           help="Limit the number of images per folder, default (0) unlimited"
                           )
cpu_set = click.option("--cpuset-cpus", type=str, default=None,
                       help="Limit the docker excecution to these CPUs. See https://docs.docker.com/config/containers/resource_constraints/#cpu"
                       )


@click.group()
@click.option("--profile", is_flag=True)
@verbose_arg
def cli(profile: bool, verbose: int) -> None:
    logging.root.setLevel(['WARNING', 'INFO', 'DEBUG'][verbose])
    if profile:
        import cProfile
        import atexit

        logger.debug("Profiling...")
        pr = cProfile.Profile()
        pr.enable()

        def exit():
            pr.disable()
            profile_name = __name__+".prof"
            pr.dump_stats(profile_name)
            logger.debug("Profiling completed")
            logger.debug("View results with snakeviz "+profile_name)

        atexit.register(exit)


@cli.command()
@folder_arg
@outdir_arg
@dry_run_arg
@overwrite_arg
@num_img_arg
@cpu_set
def many(folder, **kwargs):
    DataProcessor(**kwargs).process_folders(folder)


@cli.command()
@folder_arg
@outdir_arg
@dry_run_arg
@overwrite_arg
@num_img_arg
@cpu_set
def one(folder, **kwargs):
    DataProcessor(**kwargs).process_folder(folder)
