from typing import Callable, Generator
import pathlib

import pytest

from backend import storage


TEST_OBJECTS_ROOT = 'root/child'
TEST_DUMMY_OBJECT = f'{TEST_OBJECTS_ROOT}/test-dummy-object'


@pytest.fixture(scope='module')
def s3(clear_cache) -> storage.S3Storage:
    s3_storage = storage.s3_factory('test-bucket')
    yield s3_storage
    if clear_cache:
        s3_storage.clear()


@pytest.fixture
def dummy_file() -> Callable[[pytest.TempPathFactory], Generator[pathlib.Path, None, None]]:
    def dummy(tmp_path_factory: pytest.TempPathFactory) -> Generator[pathlib.Path, None, None]:
        while True:
            file = tmp_path_factory.mktemp(__name__) / 'dummy-file'
            with open(file.absolute(), 'wt') as fd:
                fd.write('dummy-content')
            yield file
    return dummy


@pytest.fixture
def dummy_object(s3, tmp_path_factory, dummy_file) -> Callable[[str], str]:
    def dummy(object_name: str = TEST_DUMMY_OBJECT):
        file = next(dummy_file(tmp_path_factory))
        object_name = object_name or TEST_DUMMY_OBJECT
        s3.put(file, object_name)
        return object_name
    return dummy


def test_s3_get(s3, tmp_path_factory, dummy_file):
    file = next(dummy_file(tmp_path_factory))
    object_name = f'{TEST_OBJECTS_ROOT}/test-s3-get'
    s3.put(file, object_name)
    out_file = next(dummy_file(tmp_path_factory))
    s3.get(object_name, out_file)


def test_s3_list(s3, tmp_path_factory, dummy_object):
    dummy_object()
    prefix = f'{TEST_OBJECTS_ROOT}/test-s3-list'
    dummy_object(prefix)
    keys = list(s3.list(prefix=prefix))
    assert len(keys)
    for key in keys:
        assert key.startswith(prefix)


def test_s3_delete(s3, dummy_object, tmp_path_factory, dummy_file):
    key = dummy_object()
    s3.delete(key)
    with pytest.raises(storage.S3NotFoundException):
        s3.get(key, next(dummy_file(tmp_path_factory)))
