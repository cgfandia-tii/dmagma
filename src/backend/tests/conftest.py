import pytest

from os import getenv

from backend import schema


CLEAR_CACHE = int(getenv("CLEAR_CACHE", "0"))


@pytest.fixture(scope="session")
def clear_cache() -> bool:
    return bool(CLEAR_CACHE)


@pytest.fixture
def fuzzer() -> str:
    return "libfuzzer"


@pytest.fixture
def target() -> str:
    return "libpng"


@pytest.fixture
def target_2() -> str:
    return "libtiff"


@pytest.fixture
def program() -> str:
    return "libpng_read_fuzzer"


@pytest.fixture
def program_2() -> str:
    return "tiff_read_rgba_fuzzer"


@pytest.fixture
def campaign_id() -> str:
    return "7f1bb921-74dd-490c-a8cd-f5deae6174f0"


@pytest.fixture
def campaign(
    campaign_id, fuzzer, target, target_2, program, program_2
) -> schema.Campaign:
    program = schema.Program(name=program)
    program_2 = schema.Program(name=program_2)
    target = schema.Target(name=target, programs=[program])
    target_2 = schema.Target(name=target_2, programs=[program_2])
    fuzzers = [schema.Fuzzer(name=fuzzer, targets=[target, target_2])]
    return schema.Campaign(id=campaign_id, poll=1, timeout=10, fuzzers=fuzzers)
