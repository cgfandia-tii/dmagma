# Only 1 worker per VM (-c 1) over the "fuzzing-queue" queue
celery -A backend.worker.tasks worker -c 1 -Q fuzzing-queue "$@"