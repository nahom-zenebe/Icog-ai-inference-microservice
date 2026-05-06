# AI Inference Microservice

This repo implements an AI inference microservice using **gRPC** with **all four communication models** (unary, server-streaming, client-streaming, bidirectional streaming), backed by **Gemini** (with a safe local mock fallback), and deployed behind an **Nginx Layer-7 HTTP/2 gRPC load balancer**.

## Repo layout

- protos/ai_inference.proto — strict API contract
- server/ — gRPC backend (Python), Dockerfile, auth interceptor
- client/ — CLI tester that hits Nginx (not backend directly)
- nginx/nginx.conf — HTTP/2 + `grpc_pass` reverse proxy to 3 backends
- docker-compose.yml — spins up Nginx + 3 backend replicas
- Makefile — handy commands (`make proto`, `make up`, etc.)

## Prereqs

- Docker Desktop 
- Python 3.11+

## Quickstart 

1. Create env file:
   - `cp .env.example .env`
   - Set `GEMINI_API_KEY` if you want real Gemini responses (optional).

2. Start the stack:
   - `make up`

3. In another terminal, run the CLI tester (connects to Nginx on `localhost:8080`):
   - `PYTHONPATH=client python3 client/cli.py --host localhost:8080 --token my-secret-key`

What you should see:
- Unary sentiment call **times out** (deadline demo)
- Server-streaming prints tokens as they arrive
- Client-streaming returns one summary
- Bidi chat streams assistant output token-by-token

### If you see “Cannot connect to the Docker daemon”

Start Docker Desktop, then re-run `make up`.

## Local dev (no Docker)

This is just for sanity-checking code; it does **not** include Nginx LB.

1. Install deps:
   - `python3 -m pip install -r server/requirements.txt -r client/requirements.txt`

2. Generate stubs:
   - `make proto`

3. Run the server:
   - `PYTHONPATH=server AUTH_BEARER_TOKEN=my-secret-key python3 server/main.py`

4. Run the client directly against the server:
   - `PYTHONPATH=client python3 client/cli.py --host localhost:50051 --token my-secret-key`

## API contract

The service is defined in protos/ai_inference.proto:

- Unary: `AnalyzeSentiment(text) -> (label, confidence)`
- Server-stream: `GenerateStream(prompt) -> stream token`
- Client-stream: `SummarizeStream(stream chunks) -> summary`
- Bidi-stream: `Chat(stream messages) <-> stream messages`

## Bonus tasks implemented

### 1) gRPC server interceptor as “bouncer”

- Server requires `authorization` metadata:
  - `Authorization: Bearer my-secret-key`
- Missing/wrong key returns `UNAUTHENTICATED` immediately (no AI work).

Implementation: server/auth_interceptor.py

### 2) Deadlines demo (2s client, 3s server)

- Client sets `timeout=2.0` on `AnalyzeSentiment`
- Server sleeps `SENTIMENT_DELAY_SECONDS` (defaults to `3`)
- Client catches `DEADLINE_EXCEEDED` and prints a friendly message

Implementation:
- client/cli.py
- server/service.py

## Architecture + tradeoffs (what/why)

- gRPC over HTTP/2 is chosen for **low-latency streaming** and strict contracts.
- Server-streaming models “typing” token delivery; REST typically needs chunked responses/WebSockets.
- Client-streaming is efficient for ingesting large inputs without huge single request bodies.
- Bidi streaming allows full-duplex chat without polling.

Tradeoffs vs REST:
- Pros: binary framing, codegen, streaming primitives, deadlines, metadata, interceptors.
- Cons: harder debugging without tooling, browser clients need gRPC-web, load balancing needs HTTP/2-aware proxies.

## Nginx load balancing

Nginx is configured for HTTP/2 and gRPC proxying:

- nginx/nginx.conf:
  - `listen 8080 http2;`
  - `grpc_pass grpc://grpc_backends;` (round-robin across 3 backends)

## Screenshot 
<img width="1172" height="357" alt="Screenshot 2026-05-06 at 5 02 36 PM" src="https://github.com/user-attachments/assets/88ec798f-3c34-474a-96e8-a23be60ab9a8" />
<img width="1459" height="639" alt="Screenshot 2026-05-06 at 4 37 08 PM" src="https://github.com/user-attachments/assets/c663bea8-9d8d-418c-91ee-9724c024a617" />
<img width="1166" height="522" alt="Screenshot 2026-05-06 at 5 03 18 PM" src="https://github.com/user-attachments/assets/bcb675d9-2ddf-410d-9432-d77cd04b069a" />





