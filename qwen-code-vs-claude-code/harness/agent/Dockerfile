FROM node:24-bookworm
# 道具(sqlite3 のコマンドは前作の課題 B2_07 のため入れない)
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3-venv python3-pip python3-pytest zip unzip jq file tree \
      ffmpeg imagemagick webp espeak-ng tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn \
      poppler-utils qpdf libimage-exiftool-perl nkf \
      python3-pandas python3-openpyxl python3-matplotlib python3-bs4 python3-pypdf python3-pil \
      cmake build-essential ca-certificates gnupg curl apt-transport-https \
    && rm -rf /var/lib/apt/lists/*
# whisper.cpp(文字起こし)と英語の base モデル
RUN git clone --depth 1 --branch v1.7.6 https://github.com/ggml-org/whisper.cpp /opt/whisper.cpp \
    && cmake -S /opt/whisper.cpp -B /opt/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_TESTS=OFF -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.2-a+fp16 \
    && cmake --build /opt/whisper.cpp/build -j 6 --target whisper-cli \
    && ln -s /opt/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli \
    && mkdir -p /opt/whisper-models && curl -L -o /opt/whisper-models/ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
# gcloud と Terraform
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com bookworm main" > /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update && apt-get install -y --no-install-recommends google-cloud-cli terraform && rm -rf /var/lib/apt/lists/*
# Terraform の google プロバイダを固定してミラーに置く(測定中はレジストリに出さない)
RUN mkdir -p /opt/tfmirror /tmp/tfm && printf 'terraform {\n  required_providers {\n    google = { source = "hashicorp/google", version = "7.8.0" }\n    random = { source = "hashicorp/random", version = "3.7.2" }\n  }\n}\n' > /tmp/tfm/main.tf \
    && cd /tmp/tfm && terraform providers mirror -platform=linux_arm64 /opt/tfmirror && rm -rf /tmp/tfm
RUN printf 'provider_installation {\n  filesystem_mirror {\n    path = "/opt/tfmirror"\n  }\n  direct {\n    exclude = ["registry.terraform.io/*/*"]\n  }\n}\n' > /etc/terraformrc
ENV TF_CLI_CONFIG_FILE=/etc/terraformrc CLOUDSDK_CORE_DISABLE_PROMPTS=1
# Qwen Code
RUN npm install -g @qwen-code/qwen-code@0.25.2 @anthropic-ai/claude-code@2.1.302 && npm cache clean --force \
    && chmod -R a+rX /usr/local/lib/node_modules/@qwen-code && find /usr/local/lib/node_modules/@qwen-code -path '*ripgrep*' -name rg -exec chmod a+x {} \;
RUN useradd -m -s /bin/bash agent
USER agent
RUN mkdir -p /home/agent/.qwen
WORKDIR /work
