import logging
import pathlib
import tarfile
import uuid
from os import getenv
from typing import Callable, Generator

import pytest
import docker
from docker import errors as docker_errors

from backend import storage
from backend.worker import utils, service

BUILT_IMAGES = set()
POLL = 1
TIMEOUT = '10s'


@pytest.fixture(scope='module', autouse=True)
def docker_ctx(clear_cache) -> docker.DockerClient:
    client = docker.from_env()
    yield client
    if clear_cache:
        for image in BUILT_IMAGES:
            try:
                client.images.get(image)
                client.images.remove(image=image, force=True)
            except docker_errors.ImageNotFound as e:
                logging.warning(f'Unable to find "{image}": {e}')


@pytest.fixture
def pipeline_id() -> Callable[[], Generator[str, None, None]]:
    def dummy() -> Generator[str, None, None]:
        while True:
            yield str(uuid.uuid4())
    return dummy


@pytest.fixture
def fuzzer_image(fuzzer, target) -> str:
    service.build(fuzzer, target)
    image = service.get_image_name(fuzzer, target)
    BUILT_IMAGES.add(service.get_image_name(fuzzer, target))
    return image


@pytest.fixture
def fuzzer_results(fuzzer_image, fuzzer, target, program) -> Callable[[pathlib.Path], pathlib.Path]:
    def dummy(results_dir: pathlib.Path) -> pathlib.Path:
        workdir, shared = service.get_workdir_and_shared(results_dir)
        utils.cleanup_folder(workdir)
        service.start(fuzzer, target, program, shared, POLL, TIMEOUT)
        return shared
    yield dummy


@pytest.fixture(scope='module')
def results_storage(clear_cache) -> storage.Storage:
    s3 = storage.s3_factory('test-fuzzing-results')
    yield s3
    if clear_cache:
        s3.clear()


@pytest.fixture(scope='module')
def reports_storage(clear_cache) -> storage.Storage:
    s3 = storage.s3_factory('test-reports')
    yield s3
    if clear_cache:
        s3.clear()


@pytest.fixture
def fuzz_pipeline(results_storage, campaign_id, tmp_path_factory) -> Callable[[str, str, str, str], str]:
    def dummy(pipeline_id: str, fuzzer: str, target: str, program: str):
        workdir, shared = service.get_workdir_and_shared(tmp_path_factory.mktemp(f'workdir-{pipeline_id}'))
        return service.run_fuzz_pipeline(campaign_id, pipeline_id, fuzzer, target, program, shared, workdir, POLL,
                                         TIMEOUT, results_storage)
    return dummy


def test_build(docker_ctx, fuzzer, target):
    service.build(fuzzer, target)
    image = service.get_image_name(fuzzer, target)
    docker_image = docker_ctx.images.get(image)
    assert docker_image
    BUILT_IMAGES.add(image)


def test_start(fuzzer_results, tmp_path):
    workdir = fuzzer_results(tmp_path)
    monitor_log = list((workdir / 'monitor').iterdir())
    assert len(monitor_log)


def test_pack(fuzzer_results, tmp_path_factory):
    workdir = fuzzer_results(tmp_path_factory.mktemp('workdir'))
    archived = tmp_path_factory.mktemp('archived')
    archive = service.pack(workdir, archived)
    with tarfile.open(archive.absolute(), 'r') as tar:
        assert len(tar.getmembers())


def test_run_fuzz_pipeline(results_storage, campaign_id, pipeline_id, fuzzer, target, program, tmp_path_factory):
    workdir, shared = service.get_workdir_and_shared(tmp_path_factory.mktemp('workdir'))
    tar = service.run_fuzz_pipeline(campaign_id, next(pipeline_id()), fuzzer, target, program, shared, workdir,
                                    POLL, TIMEOUT, results_storage)
    results_file = tmp_path_factory.mktemp('fuzz-results') / pathlib.Path(tar).name
    results_storage.get(tar, results_file)


def test_reduce(results_storage, reports_storage, fuzz_pipeline, campaign_id, pipeline_id, fuzzer, target, program):
    fuzz_pipeline(next(pipeline_id()), fuzzer, target, program)
    fuzz_pipeline(next(pipeline_id()), fuzzer, target, program)
    service.reduce(campaign_id, results_storage, reports_storage)
