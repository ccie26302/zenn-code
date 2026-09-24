FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY corpus.py synth.py ./
COPY data/selected_voices.json data/
ENTRYPOINT ["python", "synth.py"]
