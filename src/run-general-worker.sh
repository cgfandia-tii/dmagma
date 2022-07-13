# Workers responsible to perform general tasks (excluding the fuzzing task - fuzzing-queue)
celery -A backend.worker.tasks worker --autoscale=4,32 -X fuzzing-queue "$@"