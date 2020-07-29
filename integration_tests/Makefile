.PHONY: build test

.DEFAULT_GOAL := current

stop:
	@echo "Stopping running containers..."
	docker-compose -f docker-compose.yml -f masterV1.yml -f replicaV1.yml down --remove-orphans
	@echo "Done!"

build_current: 
	docker-compose build

build_master_v1:
	docker-compose -f docker-compose.yml -f masterV1.yml build

build_replica_v1:
	docker-compose -f docker-compose.yml -f replicaV1.yml build

current: build_current
	docker-compose run master

master_v1: build_master_v1
	docker-compose -f docker-compose.yml -f masterV1.yml run master

replica_v1: build_replica_v1
	docker-compose -f docker-compose.yml -f replicaV1.yml run master

all: build_master_v1 build_replica_v1 current master_v1 replica_v1
