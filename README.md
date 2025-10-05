# Usage
0. Download the model to junction-whisper/models: https://drive.google.com/drive/folders/1zh8Y80eb0EoMw0hpHaHu3HddO0hporzj?usp=drive_link

1. Run the applications
```
python -m pip install -r junction-backend/requirements.txt
python -m pip install -r junction-whisper/requirements.txt
docker compose up -d
python junction-whisper/app.py
python junction-backend/app.py
```

2. Open localhost
