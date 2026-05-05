import os
from concurrent import futures

import grpc

import ai_inference_pb2_grpc
from auth_interceptor import AuthInterceptor
from service import AIInferenceServicer


def serve() -> None:
    port = int(os.environ.get("PORT", "50051"))
    max_workers = int(os.environ.get("MAX_WORKERS", "10"))

    interceptors = [AuthInterceptor.from_env()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        interceptors=interceptors,
        options=[
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.keepalive_time_ms", 30_000),
            ("grpc.keepalive_timeout_ms", 10_000),
        ],
    )

    ai_inference_pb2_grpc.add_AIInferenceServicer_to_server(AIInferenceServicer(), server)

    server.add_insecure_port(f"0.0.0.0:{port}")
    server.start()

    server_id = os.environ.get("SERVER_ID", "server")
    print(f"[{server_id}] gRPC server listening on :{port}")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
