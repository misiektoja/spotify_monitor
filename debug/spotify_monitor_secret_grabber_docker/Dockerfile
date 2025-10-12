FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip xvfb \
    fonts-liberation libnss3 libxss1 libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libgtk-3-0 libx11-xcb1 libx11-6 libxcb1 libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

COPY spotify_monitor_secret_grabber_docker/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt
RUN python -m playwright install --with-deps chromium

COPY spotify_monitor_secret_grabber.py /app/spotify_monitor_secret_grabber.py
WORKDIR /app
ENTRYPOINT ["python", "/app/spotify_monitor_secret_grabber.py"]
