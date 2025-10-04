FROM python:3.11-slim

WORKDIR /app

# System dependencies (ffmpeg is required by whisper)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

ARG model

# Copy requirements and install
COPY backend .
RUN pip install -r requirements.txt
# Pre-download the whisper model during build
# whisper stores models in ~/.cache/whisper
RUN python -c "import whisper; whisper.load_model('$model')"

# Copy application files

# Set entrypoint to run app.py
ENTRYPOINT ["python", "app.py"]
