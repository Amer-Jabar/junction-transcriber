import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List


# -------------------------------
# Model Wrapper (no local weights)
# -------------------------------
class HateCategoryClassifier:
    """
    Wrapper around the pretrained HateXplain model.
    """
    def __init__(self, model_name: str = "unitary/toxic-bert"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

    def predict_logits(self, sentences: List[str]) -> torch.Tensor:
        """
        Encodes sentences and returns raw logits.
        """
        encodings = self.tokenizer(
            sentences, padding=True, truncation=True, return_tensors="pt"
        )
        with torch.no_grad():
            outputs = self.model(**encodings)
        return outputs.logits


# -------------------------------
# Inference Utility
# -------------------------------
class HateSpeechPredictor:
    """
    Clean inference interface for hate-speech category prediction.
    """
    def __init__(self):
        self.classifier = HateCategoryClassifier()
        # HateXplain labels: 0 → Hate, 1 → Offensive, 2 → Normal
        self.id2label = self.classifier.model.config.id2label
        self.label2id = self.classifier.model.config.label2id

    def predict(self, sentences: List[str]) -> List[str]:
        logits = self.classifier.predict_logits(sentences)
        preds = torch.argmax(torch.softmax(logits, dim=1), dim=1)
        return [self.id2label[p.item()] for p in preds]

    def predict_with_scores(self, sentences: List[str]):
        logits = self.classifier.predict_logits(sentences)
        probs = torch.softmax(logits, dim=1)
        results = []
        for i, sentence in enumerate(sentences):
            scores = {
                self.id2label[j]: round(probs[i, j].item(), 4)
                for j in range(len(self.id2label))
            }
            results.append({"text": sentence, "scores": scores})
        return results
