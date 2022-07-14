import pathlib
from os import getenv


SHARED_VOLUME = getenv("SHARED_VOLUME", "shared-workdir-volume")
SHARED_PATH = getenv("SHARED_PATH", "/shared-workdir")
BROKER_HOST = getenv("BROKER_HOST", "localhost")
BROKER_USER = getenv("BROKER_USER", "guest")
BROKER_PASS = getenv("BROKER_PASS", "guest")
REDIS_HOST = getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(getenv("REDIS_PORT", "6379"))
S3_ENDPOINT = getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = getenv("S3_ACCESS_KEY", "access_key")
S3_SECRET_KEY = getenv("S3_SECRET_KEY", "secret_key")
S3_REGION = getenv("S3_REGION", "us-east-1")
BUCKET_FUZZ_RESULTS = getenv("BUCKET_FUZZ_RESULTS", "fuzz-results")
BUCKET_REPORTS = getenv("BUCKET_REPORTS", "reports")
MAGMA_PATH = pathlib.Path(getenv("MAGMA_PATH", "magma"))
FUZZING_TASK_QUEUE = getenv("FUZZING_TASK_QUEUE", "fuzzing-queue")
