# AI Inference Microservice (gRPC + Gemini + Nginx L7 LB)

This repo implements an AI inference microservice using **gRPC** with **all four communication models** (unary, server-streaming, client-streaming, bidirectional streaming), backed by **Gemini** (with a safe local mock fallback), and deployed behind an **Nginx Layer-7 HTTP/2 gRPC load balancer**.

## Repo layout

- protos/ai_inference.proto — strict API contract
- server/ — gRPC backend (Python), Dockerfile, auth interceptor
- client/ — CLI tester that hits Nginx (not backend directly)
- nginx/nginx.conf — HTTP/2 + `grpc_pass` reverse proxy to 3 backends
- docker-compose.yml — spins up Nginx + 3 backend replicas
- Makefile — handy commands (`make proto`, `make up`, etc.)

## Prereqs

- Docker Desktop (for the full LB mesh)
- Python 3.11+ (for local dev)

## Quickstart (full “production-like” mesh)

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
<img width="352" height="120" alt="screenshots2" src="https://github.com/user-attachments/assets/c2bf8c2d-668a-4c19-8246-188581323e07" />
<img width="681" height="422" alt="screenshots1" src="https://github.com/user-attachments/assets/7777f431-3289-4097-b7d7-0a45476ace97" />
<img width="705" height="303" alt="screenshots" src="https://github.com/user-attachments/assets/4ebd9a70-ddbc-450d-bc9d-17225d8fe693" />





