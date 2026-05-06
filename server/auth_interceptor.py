import os
from collections.abc import Callable, Iterator
from typing import Any, Optional

import grpc


def _get_authorization_md(handler_call_details: grpc.HandlerCallDetails) -> Optional[str]:
    if handler_call_details.invocation_metadata is None:
        return None
    for k, v in handler_call_details.invocation_metadata:
        if k.lower() == "authorization":
            return v
    return None


class AuthInterceptor(grpc.ServerInterceptor):
    def __init__(self, expected_bearer_token: str) -> None:
        self._expected = f"Bearer {expected_bearer_token}".strip()

    @classmethod
    def from_env(cls) -> "AuthInterceptor":
        token = os.environ.get("AUTH_BEARER_TOKEN", "my-secret-key")
        return cls(expected_bearer_token=token)

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler = continuation(handler_call_details)
        if handler is None:
            return handler

        def deny(request_or_iterator: Any, context: grpc.ServicerContext) -> Any:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing/invalid API key")

        def authorized() -> bool:
            provided = _get_authorization_md(handler_call_details)
            return provided == self._expected

        if authorized():
            return handler

        if handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                lambda req, ctx: deny(req, ctx),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.unary_stream:
            return grpc.unary_stream_rpc_method_handler(
                lambda req, ctx: deny(req, ctx),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.stream_unary:
            return grpc.stream_unary_rpc_method_handler(
                lambda it, ctx: deny(it, ctx),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        if handler.stream_stream:
            return grpc.stream_stream_rpc_method_handler(
                lambda it, ctx: deny(it, ctx),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler
