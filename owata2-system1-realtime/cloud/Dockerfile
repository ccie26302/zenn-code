# kev-4b を CUDA で /v1/systemone としてサーブする Vertex AI カスタムコンテナ。
# Mac ローカルと「同じ重み」(adapter jaredpalmer/kev-4b + base Qwen/Qwen3.5-4B-Base@1001bb4) を焼き込む。
FROM python:3.13-slim
# build-essential: Triton(GPU 向け融合カーネル)が起動時に C コンパイラで部品をビルドするため(無いと起動時に落ちた)
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates build-essential && rm -rf /var/lib/apt/lists/*
# Vertex AI の GPU ノードはドライバを /usr/local/nvidia に差し込む。python:slim は場所を知らず、kev が黙って CPU で起動した
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility PATH=/usr/local/nvidia/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
COPY --from=ghcr.io/astral-sh/uv:0.8.12 /uv /usr/local/bin/uv
ENV HF_HOME=/opt/hf HF_HUB_DISABLE_PROGRESS_BARS=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN git clone https://github.com/jaredpalmer/kev.git /app && git -C /app checkout 0fe8fc97c2bcc247fa3efb6e5c32af4e99770e91
RUN uv sync --extra serve --frozen --no-dev
# modal_app.py と同じ高速化カーネル(Qwen3.5 の線形注意)
RUN uv pip install "flash-linear-attention==0.5.2" "triton>=3.7.1" && \
    uv pip install --no-deps "https://github.com/Dao-AILab/causal-conv1d/releases/download/v1.7.0/causal_conv1d-1.7.0%2Bcu12torch2.8cxx11abiTRUE-cp313-cp313-linux_x86_64.whl"
# 重みを焼き込む(起動時の HF ダウンロードを避ける)
RUN uv run --no-sync python -c "from huggingface_hub import snapshot_download as s; s('jaredpalmer/kev-4b'); s('Qwen/Qwen3.5-4B-Base', revision='1001bb4d826a52d1f399e183466143f4da7b741b')"
ENV HF_HUB_OFFLINE=1
EXPOSE 8080
CMD ["uv","run","--no-sync","python","-m","kev.serve","--run","jaredpalmer/kev-4b","--host","0.0.0.0","--port","8080"]
