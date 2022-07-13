import pathlib

import pytest


@pytest.fixture(scope='session')
def report_json_file() -> pathlib.Path:
    return pathlib.Path(__file__).parent / 'fixtures' / 'report.json'
