FROM python:3.11-slim

WORKDIR /app

# System dependencies (ffmpeg is required by whisper)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
RUN pip install --no-cache-dir openai-whisper
# Pre-download the whisper model during build
# whisper stores models in ~/.cache/whisper

ARG model

RUN python -c "import whisper; whisper.load_model('$model')"

# Copy application files
COPY src .

# Set entrypoint to run app.py
ENTRYPOINT ["python", "app.py"]
