FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 xvfb xauth dbus-x11 libgtk-3-0 libnss3 libasound2 libgbm1 libxss1 libatk-bridge2.0-0 libx11-xcb1 libdrm2 libxkbcommon0 libcups2 libgl1 fonts-liberation file && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 tester
