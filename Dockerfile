FROM python:3.12-slim as builder

# This flag is important to output python logs correctly in docker!
ENV PYTHONUNBUFFERED 1
# Flag to optimize container size a bit by removing runtime python cache
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /vpn_dan_bot

COPY requirements.txt \
    _main.py \
    _serv.py \
    .env \
    log.ini \
    README.md \
    .secrets/id_rsa_wg \
    ./
# RUN mkdir bugs logs && touch logs/queue.log
# RUN pip install poetry && poetry config virtualenvs.in-project true && poetry install --no-root
RUN mkdir tmp vpn_dan_bot && \
    touch vpn_dan_bot/__init__.py && \
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && \
    apt update && apt install -y --no-install-recommends postgresql-client jq curl procps

COPY src src/
COPY server server/

# CMD [ "python", "-m", "poetry", "show", "-t" ]
CMD ["/bin/bash"]
# CMD ["./_main.py"]