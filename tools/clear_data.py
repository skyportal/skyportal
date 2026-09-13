import shutil
import sys
from pathlib import Path

from baselayer.app.env import load_env, parser
from baselayer.log import make_log

log = make_log("clear_data")

basedir = Path(__file__).parent.parent.absolute()

DATA_FOLDERS = [
    ("cache_folder", "cache"),
    ("comments_folder", "persistentdata/comments"),
    ("localizations_folder", "persistentdata/localizations"),
    ("photometric_series_folder", "persistentdata/phot_series"),
    ("analysis_services.analysis_folder", "persistentdata/analysis"),
]


def resolve(folder):
    path = Path(folder)
    if not path.is_absolute():
        path = basedir / path
    path = path.resolve()

    if path == path.parent or path == basedir or path in basedir.parents:
        log(f"refusing to clear [{path}]")
        return None
    return path


def clear(path):
    if not path.is_dir():
        return

    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    log(f"cleared [{path}]")


if __name__ == "__main__":
    parser.add_argument(
        "-y", "--yes", action="store_true", help="do not ask for confirmation"
    )
    env, cfg = load_env()

    folders = [cfg.get(key, default) for key, default in DATA_FOLDERS]
    folders.append("static/thumbnails")

    paths = [path for path in map(resolve, folders) if path is not None]

    if paths and not env.yes:
        print("\nThe following data will be permanently deleted:\n")
        for path in paths:
            print(f"  {path}")
        if input("\nType 'yes' to continue: ").strip().lower() != "yes":
            log("aborted")
            sys.exit(1)

    for path in paths:
        clear(path)
