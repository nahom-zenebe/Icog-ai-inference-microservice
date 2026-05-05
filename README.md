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

## Screenshot requirement

After you run the CLI successfully against Nginx, take a terminal screenshot and add it to your submission (e.g., `docs/screenshot.png`).

## Paper reading: “On Designing and Deploying Internet-Scale Services” (Hamilton)

High-level takeaways (how it connects to this project):

- **Operations-friendly design beats heroic ops**: Hamilton argues many ops problems originate in design; services should self-detect and self-recover from common failures.
- **Expect failure**: components fail frequently at scale; recovery paths must be simple and exercised.
- **Keep it simple & automate everything**: simplicity enables automation; automation enables high system-to-admin ratios.
- **Dependency management matters**: avoid many small dependencies; depend only when the dependency is substantial or must be centralized, and implement inter-service monitoring/alerting.
- **Graceful degradation + admission control**: under overload/DOS or spikes, delivering a reduced-but-working service is better than total collapse; use admission control at the front door and also at internal boundaries.

Buzzwords (plain-English definitions):

- **Operations-friendly**: a service that can be run with minimal manual intervention; it detects and recovers from common failures automatically.
- **Design for failure**: assume machines, networks, and dependencies will break; build redundancy, timeouts, and recovery as first-class features.
- **Crash-only software**: a style where components are designed to fail/stop and restart cleanly; the failure path is the normal path.
- **Admission control / throttling**: refusing or delaying work when overloaded to avoid thrashing; often implemented via rate limits, queues, and backpressure.
- **Graceful degradation**: under stress, return partial results or reduced quality instead of hard failing for everyone.

Where this project mirrors Hamilton:
- gRPC deadlines + server sleep demo shows timeouts and failure-handling behavior
- Interceptor enforces auth at the “front door” (admission control conceptually)
- Nginx + multiple replicas demonstrates redundancy and scaling via commodity instances

