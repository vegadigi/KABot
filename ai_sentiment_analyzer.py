# ==============================================================================
# File: ai_sentiment_analyzer.py
# NEW FILE
# ==============================================================================
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class AISentimentAnalyzer:
    def __init__(self):
        print("Initializing AI Sentiment Analyzer (FinBERT)...")
        # This will download the model the first time it's run.
        model_name = "ProsusAI/finbert"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        print("FinBERT model loaded successfully.")

    def analyze(self, text):
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
            with torch.no_grad():
                logits = self.model(**inputs).logits
            scores = {k: v for k, v in zip(self.model.config.id2label.values(), torch.softmax(logits, dim=1)[0].tolist())}
            label = max(scores, key=scores.get)
            score = scores[label]
            return label, score
        except Exception as e:
            print(f"Error during FinBERT analysis: {e}")
            return "neutral", 0.0
