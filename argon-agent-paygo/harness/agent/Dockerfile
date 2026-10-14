FROM node:24-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends python3-venv python3-pip python3-pytest zip unzip jq file tree && rm -rf /var/lib/apt/lists/*
RUN npm install -g @google/gemini-cli@0.64.0 && npm cache clean --force
RUN useradd -m -s /bin/bash agent
USER agent
WORKDIR /work
RUN mkdir -p /home/agent/.gemini
