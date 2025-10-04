import os
import json
import tempfile
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from dotenv import load_dotenv
import whisper
from flask_cors import CORS
import pika
import minio

from category_classifier import HateSpeechPredictor

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/transcriber")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "roberta-large")  # You can set this in .env

# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_database()
transcripts_collection = db.transcripts

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

    temp_path = os.path.join(tempfile.gettempdir(), filename)
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

if __name__ == "__main__":
    pass
