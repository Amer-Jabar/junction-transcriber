import os
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_cors import CORS
import pika
import minio

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload

rmqConnection = pika.BlockingConnection(pika.ConnectionParameters('localhost', credentials=pika.PlainCredentials("admin", "password")))
rmqChannel = rmqConnection.channel()

detection_tasks_queue_name='detection_tasks'
rmqChannel.queue_declare(queue=detection_tasks_queue_name)
transcriptions_tasks_queue_name='transcriptions_tasks'
rmqChannel.queue_declare(queue=transcriptions_tasks_queue_name)

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
        # TODO
        pass
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
    return jsonify({"message": "The app is running."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
