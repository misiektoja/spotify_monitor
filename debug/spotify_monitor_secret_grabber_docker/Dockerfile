FROM python:3.13-slim-trixie@sha256:7ce4b6dfe35e55397b7cda544f8a13f191b7ae28dc5aad71fe664dbc9bc2623f
ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ARG APP_UID=1000
ARG APP_GID=1000

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip xvfb \
    fonts-liberation libnss3 libxss1 libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libgtk-3-0 libx11-xcb1 libx11-6 libxcb1 libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

COPY spotify_monitor_secret_grabber_docker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt
RUN python -m playwright install --with-deps chromium
# The browser and the extractor are all this image runs, so the installers are dropped from the runtime
RUN pip uninstall --yes pip setuptools wheel

COPY spotify_monitor_secret_grabber.py /app/spotify_monitor_secret_grabber.py
RUN groupadd --gid ${APP_GID} spotify-secrets && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --shell /usr/sbin/nologin spotify-secrets && mkdir -p /work && chown spotify-secrets:spotify-secrets /work
ENV HOME=/home/spotify-secrets
USER spotify-secrets
WORKDIR /work
ENTRYPOINT ["python", "/app/spotify_monitor_secret_grabber.py"]
