import os
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional
from google import genai 


@dataclass
class SentimentResult:
    label: str
    confidence: float
    model: str


class AIBackend:

    def __init__(self) -> None:
        self._api_key = os.environ.get("GEMINI_API_KEY")
        self._model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

        self._client = None
        if self._api_key:
            try: 

                self._client = genai.Client(api_key=self._api_key)
            except Exception:
              
                self._client = None

    @property
    def model_name(self) -> str:
        return self._model if self._client else "mock-local"

    def analyze_sentiment(self, text: str) -> SentimentResult:
        if not text.strip():
            return SentimentResult(label="NEUTRAL", confidence=0.5, model=self.model_name)

        if self._client is None:
            return self._mock_sentiment(text)

        prompt = (
            "Classify the sentiment of the following text as exactly one of: "
            "POSITIVE, NEGATIVE, NEUTRAL, MIXED. "
            "Return ONLY a single line JSON object with keys label and confidence (0..1).\n\n"
            f"TEXT: {text}"
        )

        try:
            resp = self._client.models.generate_content(model=self._model, contents=prompt)
            raw = getattr(resp, "text", "") or ""
           
            m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            payload = m.group(0) if m else raw
            import json

            obj = json.loads(payload)
            label = str(obj.get("label", "NEUTRAL")).upper()
            confidence = float(obj.get("confidence", 0.5))
            label = label if label in {"POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"} else "NEUTRAL"
            confidence = max(0.0, min(1.0, confidence))
            return SentimentResult(label=label, confidence=confidence, model=self._model)
        except Exception:
            return self._mock_sentiment(text)

    def generate_stream(self, prompt: str) -> Iterator[str]:
        if self._client is None:
            yield from self._mock_stream(self._mock_generate(prompt))
            return

        try:
            stream = self._client.models.generate_content_stream(model=self._model, contents=prompt)
            for chunk in stream:
                token = getattr(chunk, "text", None)
                if token:
                    yield token
        except Exception:
            yield from self._mock_stream(self._mock_generate(prompt))

    def summarize(self, text: str) -> str:
        if self._client is None:
            return self._mock_summary(text)

        prompt = (
            "Summarize the following text in 3-6 bullet points. "
            "Be concise and preserve key details.\n\n"
            f"TEXT: {text}"
        )
        try:
            resp = self._client.models.generate_content(model=self._model, contents=prompt)
            return (getattr(resp, "text", "") or "").strip() or self._mock_summary(text)
        except Exception:
            return self._mock_summary(text)

    def chat_once(self, history: list[tuple[str, str]], user_text: str) -> str:
        if self._client is None:
            return self._mock_chat(history, user_text)

       
        convo = []
        for role, text in history[-20:]:
            convo.append(f"{role.upper()}: {text}")
        convo.append(f"USER: {user_text}")
        convo.append("ASSISTANT:")
        prompt = "\n".join(convo)

        try:
            resp = self._client.models.generate_content(model=self._model, contents=prompt)
            return (getattr(resp, "text", "") or "").strip() or self._mock_chat(history, user_text)
        except Exception:
            return self._mock_chat(history, user_text)


    # Local fallback


    def _mock_sentiment(self, text: str) -> SentimentResult:
        t = text.lower()
        pos = sum(w in t for w in ["love", "great", "amazing", "perfect", "excellent", "happy"])
        neg = sum(w in t for w in ["hate", "awful", "terrible", "broken", "bad", "sad"])
        if pos and not neg:
            return SentimentResult("POSITIVE", 0.75, self.model_name)
        if neg and not pos:
            return SentimentResult("NEGATIVE", 0.75, self.model_name)
        if pos and neg:
            return SentimentResult("MIXED", 0.6, self.model_name)
        return SentimentResult("NEUTRAL", 0.55, self.model_name)

    def _mock_generate(self, prompt: str) -> str:
        return (
            "(mock) Here is a streamed response to your prompt: "
            f"{prompt.strip()}\n"
            "This simulates token-by-token generation."
        )

    def _mock_stream(self, text: str) -> Iterator[str]:
        for token in text.split(" "):
            yield token + " "
            time.sleep(0.03)

    def _mock_summary(self, text: str) -> str:
        snippet = " ".join(text.strip().split()[:60])
        if not snippet:
            return "- (mock) No content provided."
        return f"- (mock) Summary: {snippet}{'…' if len(text.split()) > 60 else ''}"

    def _mock_chat(self, history: list[tuple[str, str]], user_text: str) -> str:
        return f"(mock) You said: {user_text.strip()}"
