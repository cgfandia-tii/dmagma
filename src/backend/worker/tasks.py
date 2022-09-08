from celery import Celery, chord

from backend import config, storage, schema
from backend.worker import service


FUZZING_TASK_NAME = "fuzzing-task"
BROKER = f"amqp://{config.BROKER_USER}:{config.BROKER_PASS}@{config.BROKER_HOST}:5672"
BACKEND = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}"
app = Celery("dmagma-fuzz", broker=BROKER, backend=BACKEND)
app.conf.task_routes = {FUZZING_TASK_NAME: {"queue": config.FUZZING_TASK_QUEUE}}


@app.task(bind=True, name=FUZZING_TASK_NAME)
def fuzz(
    self,
    campaign_id: str,
    fuzzer: str,
    target: str,
    program: str,
    poll: int = 5,
    timeout: str = "1m",
):
    """
    Fuzzing task which have to be executed solely on the VM without neighbours

    :param self: Task instance
    :param campaign_id: fuzzing campaign id
    :param fuzzer: fuzzer name
    :param target: target name
    :param program: target program name
    :param poll: monitor poll interval in seconds
    :param timeout: fuzzing interval
    :return: json S3 object name
    """
    storage_in = storage.s3_factory(config.BUCKET_FUZZ_RESULTS)
    pipeline_id = self.request.id
    if not pipeline_id:
        raise service.WorkerException(
            "Fuzzing pipeline id is undefined. Running locally?"
        )
    workdir, shared = service.get_workdir_and_shared(pipeline_id)
    report = service.run_fuzz_pipeline(
        campaign_id,
        pipeline_id,
        fuzzer,
        target,
        program,
        shared,
        workdir,
        poll,
        timeout,
        storage_in,
    )
    return report


@app.task
def reduce(campaign_id: str):
    storage_in = storage.s3_factory(config.BUCKET_FUZZ_RESULTS)
    storage_out = storage.s3_factory(config.BUCKET_REPORTS)
    service.reduce(campaign_id, storage_in, storage_out)


@app.task
def start_campaign(campaign: dict) -> str:
    """
    Start the Magma benchmark campaign

    :param campaign: campaign configuration dictionary
    :return: task id of the chord of the fuzzing tasks
    """
    campaign = schema.Campaign.parse_obj(campaign)
    campaign_id = campaign.id
    fuzzing_pipelines = []
    for fuzzer in campaign.fuzzers:
        for target in fuzzer.targets:
            for program in target.programs:
                args = (
                    campaign_id,
                    fuzzer.name,
                    target.name,
                    program.name,
                    campaign.poll,
                    f"{campaign.timeout}s",
                )
                fuzzing_pipelines.append(args)
    task = chord(
        (fuzz.s(*args) for args in fuzzing_pipelines), reduce.si(campaign_id)
    ).apply_async()
    return task.id
