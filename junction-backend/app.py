import os
import tempfile
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import pika
import minio
import uuid
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

logging.info("initializing flask")

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload


logging.info("initializing mongo")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/transcriber")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_database()
transcripts_collection = db.transcripts

logging.info("initializing rabbitmq")

rmqConnection = pika.BlockingConnection(pika.ConnectionParameters('localhost', credentials=pika.PlainCredentials("admin", "password")))
rmqChannel = rmqConnection.channel()

detection_tasks_queue_name='detection_tasks'
rmqChannel.queue_declare(queue=detection_tasks_queue_name)
transcriptions_tasks_queue_name='transcriptions_tasks'
rmqChannel.queue_declare(queue=transcriptions_tasks_queue_name)


logging.info("initializing minio")

minioClient = minio.Minio("localhost:9000", secure=False, access_key="admin", secret_key="password")

audio_bucket_name = "files"
if not minioClient.bucket_exists(audio_bucket_name):
    minioClient.make_bucket(audio_bucket_name)

transcriptions_bucket_name = "transcriptions"
if not minioClient.bucket_exists(transcriptions_bucket_name):
    minioClient.make_bucket(transcriptions_bucket_name)

@app.route("/api/transcribe", methods=["POST"])
def upload_and_transcribe():
    logging.info(f"Received {request}")
    if "audio" not in request.files or request.files["audio"].filename == "":
        return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files["audio"]

    try:
        # save the file to minio files bucket with file size
        minioClient.put_object(audio_bucket_name, audio_file.filename, audio_file, length=-1, part_size=10*1024*1024)

        # generate uuid
        id = str(uuid.uuid4())

        rmqChannel.basic_publish(exchange='',
                              routing_key=transcriptions_tasks_queue_name,
                              body=json.dumps({
                                  "id": id,
                                  "filename": audio_file.filename
                              }))

        return jsonify({"filename": audio_file.filename,"transcript_id": id}), 200
    except Exception as e:
        logging.error(e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/transcript/<transcript_id>", methods=["GET"])
def get_transcript(transcript_id):
    try:
        doc = transcripts_collection.find_one({"id": transcript_id})
        if not doc:
            return jsonify({"error": "Transcript not found"}), 404
        del doc["_id"]
        return jsonify(doc)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return jsonify({"message": "Whisper Demo API is running."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
