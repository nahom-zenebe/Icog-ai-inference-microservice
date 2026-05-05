import argparse
import queue
import threading
import time
import uuid

import grpc
from rich.console import Console
from rich.panel import Panel

import ai_inference_pb2
import ai_inference_pb2_grpc


console = Console()


def md_auth(token: str) -> list[tuple[str, str]]:
    return [("authorization", f"Bearer {token}")]


class ChatStreamer:
    def __init__(self, conversation_id: str) -> None:
        self._conversation_id = conversation_id
        self._q: queue.Queue[ai_inference_pb2.ChatMessage | None] = queue.Queue()

    def send_user(self, text: str) -> None:
        self._q.put(
            ai_inference_pb2.ChatMessage(
                conversation_id=self._conversation_id,
                role="user",
                text=text,
            )
        )

    def close(self) -> None:
        self._q.put(None)

    def __iter__(self):
        return self

    def __next__(self) -> ai_inference_pb2.ChatMessage:
        item = self._q.get()
        if item is None:
            raise StopIteration
        return item


def run(host: str, token: str) -> int:
    console.print(Panel.fit(f"Connecting to gRPC LB at [bold]{host}[/bold]"))

    channel = grpc.insecure_channel(host)
    stub = ai_inference_pb2_grpc.AIInferenceStub(channel)

    # Task 2: Unary sentiment with strict deadline (bonus)
    console.rule("Task 2 — Unary Sentiment (2s deadline)")
    try:
        resp = stub.AnalyzeSentiment(
            ai_inference_pb2.SentimentRequest(
                text="I love the battery life, but the screen is awful.",
            ),
            timeout=2.0,
            metadata=md_auth(token),
        )
        label_name = ai_inference_pb2.SentimentLabel.Name(resp.label)
        console.print(
            f"label={label_name} confidence={resp.confidence:.2f} model={resp.model}"
        )
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            console.print("Sentiment call timed out (expected demo: server sleeps 3s).")
        elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
            console.print("Unauthenticated: check your Authorization token.")
        else:
            console.print(f"Unary RPC failed: {e.code().name}: {e.details()}")

    # Task 3: Server streaming generation
    console.rule("Task 3 — Server Streaming Generation")
    try:
        stream = stub.GenerateStream(
            ai_inference_pb2.GenerateRequest(prompt="Write one sentence about gRPC streaming."),
            metadata=md_auth(token),
        )
        out = []
        for msg in stream:
            out.append(msg.token)
            console.print(msg.token, end="")
        console.print("\n")
    except grpc.RpcError as e:
        console.print(f"Server-streaming RPC failed: {e.code().name}: {e.details()}")

    # Task 4: Client streaming summarization
    console.rule("Task 4 — Client Streaming Summarization")
    chunks = [
        "gRPC supports unary and streaming RPCs. ",
        "Streaming enables low-latency token delivery. ",
        "Nginx can load balance gRPC at L7 over HTTP/2. ",
    ]

    def chunk_iter():
        for c in chunks:
            time.sleep(0.05)
            yield ai_inference_pb2.SummarizeChunk(text=c)

    try:
        resp = stub.SummarizeStream(chunk_iter(), metadata=md_auth(token))
        console.print(f"model={resp.model}")
        console.print(resp.summary)
    except grpc.RpcError as e:
        console.print(f"Client-streaming RPC failed: {e.code().name}: {e.details()}")

    # Task 5: Bidirectional streaming chat
    console.rule("Task 5 — Bidi Streaming Chat")
    conversation_id = str(uuid.uuid4())
    chat = ChatStreamer(conversation_id)

    def sender():
        chat.send_user("Hi! Give me a short tip for designing gRPC APIs.")
        time.sleep(0.3)
        chat.send_user("Now list two tradeoffs of gRPC vs REST.")
        time.sleep(0.3)
        chat.close()

    t = threading.Thread(target=sender, daemon=True)
    t.start()

    try:
        responses = stub.Chat(chat, metadata=md_auth(token))
        assembled = []
        for r in responses:
            assembled.append(r.text)
            console.print(r.text, end="")
        console.print("\n")
    except grpc.RpcError as e:
        debug = getattr(e, "debug_error_string", None)
        extra = f"\n{debug()}" if callable(debug) else ""
        console.print(f"Bidi-streaming RPC failed: {e.code().name}: {e.details()}{extra}")

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="gRPC AI microservice CLI tester")
    p.add_argument("--host", default="localhost:8080", help="nginx gRPC load balancer host:port")
    p.add_argument("--token", default="my-secret-key", help="mock bearer token")
    args = p.parse_args()
    return run(args.host, args.token)


if __name__ == "__main__":
    raise SystemExit(main())
