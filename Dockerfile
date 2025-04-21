FROM python:3.12-slim

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

COPY src src/
COPY server server/

RUN mkdir -p /vpn_dan_bot/tmp /vpn_dan_bot/vpn_dan_bot && \
    chown -R 1111:1111 /vpn_dan_bot && \
    apt update && apt install -y --no-install-recommends postgresql-client jq curl procps

RUN groupadd -g 1111 bot && \
    useradd -u 1111 -g bot bot

USER 1111:1111

RUN touch vpn_dan_bot/__init__.py && \
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

CMD ["/bin/bash"]