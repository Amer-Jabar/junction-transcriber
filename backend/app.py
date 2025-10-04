import os
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from dotenv import load_dotenv
import voxtral
from flask_cors import CORS

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/transcriber")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_database()
transcripts_collection = db.transcripts

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload


def transcribe_audio(file_path):
    # Voxtral API: voxtral.transcribe returns a dict with "segments"
    result = voxtral.transcribe(file_path)
    segments = []
    for segment in result.get("segments", []):
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        text = segment.get("text", "").strip()
        segments.append(
            {
                "timestamp": {
                    "start": f"{int(start // 3600):02}:{int((start % 3600) // 60):02}:{start % 60:06.3f}",
                    "end": f"{int(end // 3600):02}:{int((end % 3600) // 60):02}:{end % 60:06.3f}",
                },
                "segment": text,
            }
        )
    return segments


@app.route("/api/transcribe", methods=["POST"])
def upload_and_transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(audio_file.filename)
    temp_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    audio_file.save(temp_path)

    try:
        segments = transcribe_audio(temp_path)
        transcript_doc = {
            "filename": filename,
            "segments": segments,
            "transcript": " ".join([s["segment"] for s in segments]),
        }
        result = transcripts_collection.insert_one(transcript_doc)

        transcript_doc["_id"] = str(result.inserted_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify(
        {
            "message": "Transcription successful",
            "transcript_id": transcript_doc["_id"],
            "filename": filename,
            "segments": segments,
            "transcript": transcript_doc["transcript"],
        }
    )


@app.route("/api/transcript/<transcript_id>", methods=["GET"])
def get_transcript(transcript_id):
    from bson.objectid import ObjectId

    try:
        doc = transcripts_collection.find_one({"_id": ObjectId(transcript_id)})
        if not doc:
            return jsonify({"error": "Transcript not found"}), 404
        doc["_id"] = str(doc["_id"])
        return jsonify(doc)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return jsonify({"message": "Whisper Demo API is running."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
