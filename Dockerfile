# syntax=docker/dockerfile:1
FROM python:3.13-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/spotify
ENV SPOTIFY_MONITOR_DOCKER=1

WORKDIR /opt/spotify_monitor

# The base image lags behind Debian security updates between its own rebuilds, so they are applied here
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
# Pillow is optional for source installs but is preinstalled here because the runtime image ships without pip, so NTFY_IMAGES can be turned on without rebuilding
# pip is only needed to install the requirements, so it is removed from the runtime image
RUN /usr/local/bin/python -m pip install --no-cache-dir -r requirements.txt "Pillow>=12.0.0" && /usr/local/bin/python -m pip uninstall --yes pip

RUN groupadd --system --gid 10001 spotify && useradd --system --uid 10001 --gid spotify --create-home --home-dir /home/spotify --shell /usr/sbin/nologin spotify

COPY spotify_monitor.py ./spotify_monitor.py

RUN chmod 755 /opt/spotify_monitor/spotify_monitor.py && mkdir -p /data && chown -R spotify:spotify /opt/spotify_monitor /data /home/spotify

WORKDIR /data
USER spotify

ENTRYPOINT ["/usr/local/bin/python", "/opt/spotify_monitor/spotify_monitor.py"]
CMD ["--help"]
