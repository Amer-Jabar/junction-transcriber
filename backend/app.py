import os
import tempfile
import json
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from dotenv import load_dotenv
import whisper
from flask_cors import CORS
import pika
import minio

from backend.category_classifier import HateSpeechPredictor


# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/transcriber")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "roberta-large")  # You can set this in .env

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

# Whisper model (load once)
whisper_model = whisper.load_model(WHISPER_MODEL)

predictor = HateSpeechPredictor()

rmqConnection = pika.BlockingConnection(pika.ConnectionParameters('localhost', credentials=pika.PlainCredentials("admin", "password")))
rmqChannel = rmqConnection.channel()

detection_tasks_queue_name='detection_tasks'
rmqChannel.queue_declare(queue=detection_tasks_queue_name)
transcriptions_tasks_queue_name='transcriptions_tasks'
rmqChannel.queue_declare(queue=transcriptions_tasks_queue_name)

def transcribe(path: str, filename: str):
    segments = transcribe_audio(path)
    transcript_doc = {
        "filename": filename,
        "segments": segments,
    }
    result = transcripts_collection.insert_one(transcript_doc)

    transcript_id = str(result.inserted_id)
    transcript_doc["_id"] = transcript_id

    rmqChannel.basic_publish(exchange='',
                          routing_key=detection_tasks_queue_name,
                          body=json.dumps({"transcript_id": transcript_id, "filename": filename}))

    return jsonify(
        {
            "message": "Transcription successful",
            "transcript_id": transcript_doc["_id"],
            "filename": filename,
            "segments": segments,
            "transcript": transcript_doc["transcript"],
        }
    )

def transcribe_audio(file_path):
    result = whisper_model.transcribe(file_path, no_speech_threshold=5)
    segments = []
    for segment in result.get("segments", []):
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()
        category = predictor.predict([text])
        segments.append(
            {
                "timestamp": {
                    "start": f"{int(start // 3600):02}:{int((start % 3600) // 60):02}:{start % 60:06.3f}",
                    "end": f"{int(end // 3600):02}:{int((end % 3600) // 60):02}:{end % 60:06.3f}",
                },
                "segment": text,
                "category": category
            }
        )
    return segments


def on_transcription_task(connection, method, properties, message):
    data = json.loads(message.decode('UTF-8'))
    filename = data["filename"]

    temp_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    minioClient.fget_object(audio_bucket_name, filename, temp_path)

    transcribe(temp_path, filename)

rmqChannel.basic_consume(queue=transcriptions_tasks_queue_name, on_message_callback=on_transcription_task, auto_ack=True)


#connect to minio with user and password
minioClient = minio.Minio("localhost:9000", secure=False, access_key="admin", secret_key="password")

audio_bucket_name = "files"
if not minioClient.bucket_exists(audio_bucket_name):
    minioClient.make_bucket(audio_bucket_name)

transcriptions_bucket_name = "transcriptions"
if not minioClient.bucket_exists(transcriptions_bucket_name):
    minioClient.make_bucket(transcriptions_bucket_name)

rmqChannel.start_consuming()


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
        return transcribe(temp_path, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

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
