FROM python:3.12-slim

# This flag is important to output python logs correctly in docker!
ENV PYTHONUNBUFFERED 1
# Flag to optimize container size a bit by removing runtime python cache
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /vpn_dan_bot

COPY src src/
COPY server server/
COPY pyproject.toml poetry.lock _main.py _serv.py .env log.ini id_rsa_wg ./
RUN mkdir tmp
# RUN mkdir bugs logs && touch logs/queue.log

RUN pip install poetry && poetry config virtualenvs.in-project true && poetry install --no-root

RUN apt update && apt install -y postgresql-client

# CMD [ "python", "-m", "poetry", "show", "-t" ]
CMD ["/bin/bash"]
# CMD ["./_main.py"]