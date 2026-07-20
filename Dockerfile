# syntax=docker/dockerfile:1
FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/spotify
ENV SPOTIFY_MONITOR_DOCKER=1

WORKDIR /opt/spotify_monitor

COPY requirements.txt ./requirements.txt
RUN /usr/local/bin/python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --system --gid 10001 spotify && useradd --system --uid 10001 --gid spotify --create-home --home-dir /home/spotify --shell /usr/sbin/nologin spotify

COPY spotify_monitor.py ./spotify_monitor.py

RUN chmod 755 /opt/spotify_monitor/spotify_monitor.py && mkdir -p /data && chown -R spotify:spotify /opt/spotify_monitor /data /home/spotify

WORKDIR /data
USER spotify

ENTRYPOINT ["/usr/local/bin/python", "/opt/spotify_monitor/spotify_monitor.py"]
CMD ["--help"]
