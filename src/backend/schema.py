from typing import List, Optional, Union

from pydantic import BaseModel, validator, constr, PositiveInt

from backend import config


NAME_CONSTRAINT = constr(regex=r'[\w-]+')
FUZZERS = {path.name for path in (config.MAGMA_PATH / 'fuzzers').iterdir()}
TARGETS = {path.name for path in (config.MAGMA_PATH / 'targets').iterdir()}


def validate_uniqueness(v: List[Union['Program', 'Target', 'Fuzzer']]):
    if len(v) != len({value.name for value in v}):
        raise ValueError('Non-unique arguments')
    return v


class Program(BaseModel):
    name: NAME_CONSTRAINT
    args: Optional[str]


class Target(BaseModel):
    name: NAME_CONSTRAINT
    programs: List[Program]

    @validator('programs')
    def unique_arguments(cls, v: List[Program]):
        return validate_uniqueness(v)

    @validator('name')
    def exists(cls, v: str):
        if v not in TARGETS:
            raise ValueError(f'Target "{v}" does not exists')
        return v


class Fuzzer(BaseModel):
    name: NAME_CONSTRAINT
    targets: List[Target]

    @validator('targets')
    def unique_arguments(cls, v: List[Target]):
        return validate_uniqueness(v)

    @validator('name')
    def exists(cls, v: str):
        if v not in FUZZERS:
            raise ValueError(f'Fuzzer "{v}" does not exists')
        return v


class Campaign(BaseModel):
    id: str
    poll: PositiveInt
    timeout: PositiveInt
    fuzzers: List[Fuzzer]

    @validator('fuzzers')
    def unique_arguments(cls, v: List[Fuzzer]):
        return validate_uniqueness(v)
