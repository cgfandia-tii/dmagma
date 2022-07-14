import pathlib
import shutil


def cleanup_folder(folder: pathlib.Path):
    for path in folder.glob("**/*"):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)


def is_docker() -> bool:
    return pathlib.Path("/.dockerenv").exists()


def remove_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text  # or whatever
