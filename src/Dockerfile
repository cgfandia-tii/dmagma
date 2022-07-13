FROM python:3.8-bullseye

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get upgrade -y && \
    apt-get install sudo docker.io -y && \
    docker --version && \
    python -m pip install --upgrade pip

RUN groupadd --gid 1000 user && \
    useradd -m -d /home/user -g user -G docker,sudo -u 1000 user

WORKDIR dmagma-fuzz

COPY requirements.txt requirements.txt

COPY magma magma

RUN pip install --no-cache-dir -r requirements.txt -r magma/tools/report_df/requirements.txt

COPY backend backend
COPY pytest.ini pytest.ini
COPY run-fuzzing-worker.sh run-fuzzing-worker.sh
COPY run-general-worker.sh run-general-worker.sh

CMD ./run-fuzzing-worker.sh -l INFO