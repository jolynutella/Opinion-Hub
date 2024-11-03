import os
from google.cloud import language_v1

class SentimentAnalyzer:
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "amiable-poet-423112-e5-532beb7e0adb.json"
        client_options = {"api_endpoint": "language.googleapis.com"}
        self.client = language_v1.LanguageServiceClient(client_options=client_options)

    def analyze_sentiment(self, text):
        document = language_v1.Document(content=text, type=language_v1.Document.Type.PLAIN_TEXT)
        sentiment = self.client.analyze_sentiment(request={"document": document}).document_sentiment
        
        return sentiment.score
