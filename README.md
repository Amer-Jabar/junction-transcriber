# Whisper Demo

A modernized audio transcription service using OpenAI Whisper, Flask, MongoDB, and a simple web UI.

---

## Features

- **Audio Transcription:** Upload audio files and get timestamped transcripts using Whisper.
- **MongoDB Integration:** Transcription results are stored in MongoDB for retrieval and analysis.
- **Web UI:** Simple HTML/JS frontend for uploading audio and viewing transcripts.
- **REST API:** Flask backend exposes endpoints for audio upload and transcript retrieval.
- **Docker Support:** Containerized for easy deployment.

---

## Project Structure

```
transcriber/
├── backend/         # Flask API, Whisper integration, MongoDB logic
│   ├── app.py
│   └── requirements.txt
├── config/          # Environment variable templates
│   └── .env.example
├── frontend/        # Static HTML/JS frontend
│   └── index.html
├── audio.mp3        # Example audio file
├── output.json      # Example output (legacy)
├── Dockerfile       # Container setup
└── README.md        # This file
```

---

## Setup

### 1. Clone the Repository

```sh
git clone <repo-url>
cd transcriber
```

### 2. Install Dependencies

#### Python (Backend)

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### MongoDB

- Install and run MongoDB locally, or use a cloud MongoDB service.
- Update `config/.env.example` with your MongoDB URI.

#### Whisper Model

- The backend loads the Whisper model specified in `.env` (default: `tiny`).

### 3. Environment Variables

Copy and edit the example env file:

```sh
cp config/.env.example config/.env
```

Set your values for:

- `MONGO_URI`
- `FLASK_SECRET_KEY`
- `WHISPER_MODEL` (optional)

### 4. Run the Backend

```sh
cd backend
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

Or, run directly:

```sh
python app.py
```

### 5. Run the Frontend

Open `frontend/index.html` in your browser.

> For local development, you may need to serve the frontend via a simple HTTP server (e.g., `python -m http.server`) and proxy API requests to Flask.

---

## Usage

1. Run `python backend/app.py`
2. Run `docker compose up -d --build`
3. Go to `http://localhost:8080` in your browser.

---

## API Endpoints

### `POST /api/transcribe`

- **Body:** `multipart/form-data` with `audio` file.
- **Response:** JSON with transcript, segments, transcript ID.

### `GET /api/transcript/<transcript_id>`

- **Response:** JSON with transcript details.
