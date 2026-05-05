.PHONY: proto server client up down logs

PYTHON ?= python3

proto:
	$(PYTHON) -m grpc_tools.protoc -I./protos \
		--python_out=./server --grpc_python_out=./server \
		./protos/ai_inference.proto
	$(PYTHON) -m grpc_tools.protoc -I./protos \
		--python_out=./client --grpc_python_out=./client \
		./protos/ai_inference.proto

server:
	PYTHONPATH=server $(PYTHON) server/main.py

client:
	PYTHONPATH=client $(PYTHON) client/cli.py

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f
