#!/bin/bash

set -e

echo "Running backward compatibility tests....."

if [ -n "$DOCKER_USERNAME" ] && [ -n "$DOCKER_PASSWORD" ]; then
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

cd integration_tests
docker compose -f docker-compose.yml -f masterV1.yml build
docker compose -f docker-compose.yml -f masterV1.yml run master
docker compose -f docker-compose.yml -f masterV1.yml down --remove-orphans

docker compose -f docker-compose.yml -f replicaV1.yml build
docker compose -f docker-compose.yml -f replicaV1.yml run master
docker compose -f docker-compose.yml -f replicaV1.yml down --remove-orphans
cd ..

echo "Done!"
