import pytest

import pydantic

from backend import schema


def test_valid_fuzzer(fuzzer, target, program):
    program = schema.Program(name=program)
    target = schema.Target(name=target, programs=[program])
    schema.Fuzzer(name=fuzzer, targets=[target])


def test_invalid_fuzzer(target, program):
    program = schema.Program(name=program)
    target = schema.Target(name=target, programs=[program])
    with pytest.raises(pydantic.ValidationError) as e:
        schema.Fuzzer(name="unknown-fuzzer-name", targets=[target])
    assert "not exists" in str(e.value)


def test_invalid_target(program):
    program = schema.Program(name=program)
    with pytest.raises(pydantic.ValidationError) as e:
        schema.Target(name="unknown-target-name", programs=[program])
    assert "not exists" in str(e.value)
