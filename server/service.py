import os
import threading
import time
from collections import defaultdict
from collections.abc import Iterator

import grpc

import ai_inference_pb2
import ai_inference_pb2_grpc
from ai_backend import AIBackend


_LABEL_TO_ENUM = {
    "POSITIVE": ai_inference_pb2.POSITIVE,
    "NEGATIVE": ai_inference_pb2.NEGATIVE,
    "NEUTRAL": ai_inference_pb2.NEUTRAL,
    "MIXED": ai_inference_pb2.MIXED,
}


class AIInferenceServicer(ai_inference_pb2_grpc.AIInferenceServicer):
    def __init__(self) -> None:
        self._ai = AIBackend()
        self._server_id = os.environ.get("SERVER_ID", "server")
        self._history: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self._lock = threading.Lock()

    # Task 2: Unary
    def AnalyzeSentiment(
        self, request: ai_inference_pb2.SentimentRequest, context: grpc.ServicerContext
    ) -> ai_inference_pb2.SentimentResponse:
        # Bonus: server intentionally sleeps longer than client deadline.
        delay = float(os.environ.get("SENTIMENT_DELAY_SECONDS", "3"))
        if delay > 0:
            time.sleep(delay)

        result = self._ai.analyze_sentiment(request.text)
        return ai_inference_pb2.SentimentResponse(
            label=_LABEL_TO_ENUM.get(result.label, ai_inference_pb2.NEUTRAL),
            confidence=result.confidence,
            model=f"{result.model}@{self._server_id}",
        )

    # Task 3: Server streaming
    def GenerateStream(
        self, request: ai_inference_pb2.GenerateRequest, context: grpc.ServicerContext
    ) -> Iterator[ai_inference_pb2.GenerateStreamResponse]:
        for token in self._ai.generate_stream(request.prompt):
            if not context.is_active():
                return
            yield ai_inference_pb2.GenerateStreamResponse(token=token)

    # Task 4: Client streaming
    def SummarizeStream(
        self, request_iterator: Iterator[ai_inference_pb2.SummarizeChunk], context: grpc.ServicerContext
    ) -> ai_inference_pb2.SummarizeResponse:
        chunks: list[str] = []
        for chunk in request_iterator:
            if chunk.text:
                chunks.append(chunk.text)

        aggregated = "".join(chunks)
        summary = self._ai.summarize(aggregated)
        return ai_inference_pb2.SummarizeResponse(
            summary=summary,
            model=f"{self._ai.model_name}@{self._server_id}",
        )

    # Task 5: Bidi streaming
    def Chat(
        self, request_iterator: Iterator[ai_inference_pb2.ChatMessage], context: grpc.ServicerContext
    ) -> Iterator[ai_inference_pb2.ChatMessage]:
        for msg in request_iterator:
            if not context.is_active():
                return

            conversation_id = msg.conversation_id or "default"
            user_text = (msg.text or "").strip()
            if not user_text:
                continue

            with self._lock:
                history = self._history[conversation_id]
                history.append(("user", user_text))
                snapshot = list(history)

            assistant_text = self._ai.chat_once(snapshot, user_text)

            with self._lock:
                self._history[conversation_id].append(("assistant", assistant_text))

            # Stream assistant response as token chunks
            for token in assistant_text.split(" "):
                if not context.is_active():
                    return
                yield ai_inference_pb2.ChatMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    text=token + " ",
                )
                time.sleep(0.02)
