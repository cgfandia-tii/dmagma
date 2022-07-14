import subprocess
import logging
import pathlib
import tempfile
from typing import Tuple

from backend import config, exceptions
from backend.worker.utils import cleanup_folder, is_docker, remove_prefix
from backend.storage import Storage

LOGGING_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)
logger = logging.getLogger("worker")
CAPTAIN_PATH = config.MAGMA_PATH / "tools/captain"
BENCHD_PATH = config.MAGMA_PATH / "tools/benchd"
REPORT_DF_PATH = config.MAGMA_PATH / "tools/report_df"


class WorkerException(exceptions.BackendException):
    pass


def get_image_name(fuzzer: str, target: str) -> str:
    return f"magma/{fuzzer}/{target}"


def shell_wrapper(cmd: str, cwd: pathlib.Path = None, comment: str = None) -> str:
    if comment:
        logger.info(comment)
    logger.debug(cmd)
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, shell=True, text=True, check=True
    )
    logger.debug(result.stdout)
    return str(result.stdout)


def build(fuzzer: str, target: str):
    cmd = f"FUZZER={fuzzer} TARGET={target} ./build.sh"
    shell_wrapper(
        cmd, CAPTAIN_PATH, f'Building "{get_image_name(fuzzer, target)}" image...'
    )


def get_workdir_and_shared(
    tmp_workdir: pathlib.Path = None,
) -> Tuple[pathlib.Path, str]:
    if is_docker() or not tmp_workdir:
        workdir = pathlib.Path(config.SHARED_PATH)
        if not workdir.exists():
            logger.warning(f'Shared workdir "{workdir}" does not exist, creating...')
            workdir.mkdir(parents=True, exist_ok=True)
        shared = config.SHARED_VOLUME
    else:
        workdir = tmp_workdir
        shared = workdir.absolute()
    return workdir, shared


def start(fuzzer: str, target: str, program: str, shared: str, poll: int, timeout: str):
    cmd = f"FUZZER={fuzzer} TARGET={target} PROGRAM={program} \
        SHARED={shared} POLL={poll} TIMEOUT={timeout} ./start.sh"
    shell_wrapper(cmd, CAPTAIN_PATH, "Fuzzing has been started...")


def pack(workdir: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    if not len(list(workdir.iterdir())):
        raise WorkerException("Workdir is empty, nothing to gather")
    archive = out_dir / "ball.tar"
    cmd = f'tar -cf "{archive.absolute()}" -C "{workdir.absolute()}" .'
    shell_wrapper(cmd, comment="Packing...")
    return archive


def run_fuzz_pipeline(
    campaign_id: str,
    pipeline_id: str,
    fuzzer: str,
    target: str,
    program: str,
    shared: str,
    workdir: pathlib.Path,
    poll: int,
    timeout: str,
    storage: Storage,
):
    """
    Perform fuzzing and save results to storage

    :param campaign_id: benchmark campaign id
    :param pipeline_id: fuzzing process id (task id)
    :param fuzzer: fuzzer name
    :param target: target name
    :param program: target program name
    :param shared: shared path(volume) between host and fuzzing container
    :param workdir: local worker path with results of the fuzzing container
    :param poll: monitor poll delay
    :param timeout: fuzzing process timeout
    :param storage: storage for the fuzzing results
    :return: object name of the results in the storage
    """
    cleanup_folder(workdir)
    build(fuzzer, target)
    start(fuzzer, target, program, shared, poll, timeout)
    with tempfile.TemporaryDirectory(pipeline_id, campaign_id) as tmp_dir:
        tar = pack(workdir, pathlib.Path(tmp_dir))
        name = tar.name
        path = f"{campaign_id}/{fuzzer}/{target}/{program}/{pipeline_id}/{name}"
        storage.put(tar, path)
        return path


def get_report_key(campaign_id: str) -> str:
    return f"{campaign_id}.json"


def reduce(campaign_id, fuzz_storage: Storage, reports_storage: Storage):
    with tempfile.TemporaryDirectory(prefix=campaign_id) as tmp_dir:
        tmp_dir = pathlib.Path(tmp_dir)
        workdir = tmp_dir / "workdir"
        ar = workdir / "ar"
        ar.mkdir(parents=True, exist_ok=True)
        for key in fuzz_storage.list(prefix=campaign_id):
            result_path = ar / remove_prefix(key, campaign_id).strip("/")
            result_path.parent.mkdir(parents=True, exist_ok=True)
            fuzz_storage.get(key, result_path)
        report = tmp_dir / "report.json"
        workdir_p = workdir.resolve()
        report_p = report.resolve()
        cmd = f'python {BENCHD_PATH / "exp2json.py"} {workdir_p} {report_p}'
        shell_wrapper(cmd, comment="Generating JSON report...")
        reports_storage.put(report, get_report_key(campaign_id))
