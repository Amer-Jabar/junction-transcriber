import sys
import whisper


def transcribe(file_name: str, model: str):
    model = whisper.load_model(model)
    result = model.transcribe(file_name, no_speech_threshold=5)

    data = []
    for i, segment in enumerate(result["segments"], start=1):
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()

        segment = { "timestamp": {} }
        segment["timestamp"]["start"] = f"{int(start // 3600):02}:{int((start % 3600) // 60):02}:{start % 60:06.3f}"
        segment["timestamp"]["end"] = f"{int(end // 3600):02}:{int((end % 3600) // 60):02}:{end % 60:06.3f}"
        segment["segment"] = text
        data.append(segment)
    return data


def write(file_name, data):
    with open(file_name, 'w') as f:
        f.write(str(data))


model = sys.argv[1]
input_file_name = sys.argv[2]
output_file_name = sys.argv[3]


result = transcribe(input_file_name, model)
write_to_file(output_file_name, result)
