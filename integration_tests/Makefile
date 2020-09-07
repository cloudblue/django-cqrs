.PHONY: build test

.DEFAULT_GOAL := pika

build: 
	docker-compose build

build_master_v1:
	docker-compose -f docker-compose.yml -f masterV1.yml build

build_replica_v1:
	docker-compose -f docker-compose.yml -f replicaV1.yml build

pika: build
	@echo "Run PIKA integration tests..."
	docker-compose run master
	@echo "Stopping running containers..."
	docker-compose down --remove-orphans
	@echo "Done!"

kombu: build
	@echo "Run KOMBU integration tests..."
	docker-compose -f docker-compose.yml -f kombu.yml run master
	@echo "Stopping running containers..."
	docker-compose -f docker-compose.yml -f kombu.yml down --remove-orphans
	@echo "Done!"

master_v1: build_master_v1
	@echo "Run regression tests Master v1.3.1..."
	docker-compose -f docker-compose.yml -f masterV1.yml run master
	@echo "Stopping running containers..."
	docker-compose -f docker-compose.yml -f masterV1.yml down --remove-orphans
	@echo "Done!"

replica_v1: build_replica_v1
	@echo "Run regression tests Replica v1.3.1..."
	docker-compose -f docker-compose.yml -f replicaV1.yml run master
	@echo "Stopping running containers..."
	docker-compose -f docker-compose.yml -f replicaV1.yml down --remove-orphans
	@echo "Done!"

all: pika kombu master_v1 replica_v1
