FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY protos /app/protos
COPY server /app/server

RUN python -m grpc_tools.protoc -I/app/protos \
    --python_out=/app/server --grpc_python_out=/app/server \
    /app/protos/ai_inference.proto

ENV PYTHONPATH=/app/server
EXPOSE 50051

CMD ["python", "/app/server/main.py"]
