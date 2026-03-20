#!/bin/bash

set -e

echo "Running integration tests....."

if [ -n "$DOCKER_USERNAME" ] && [ -n "$DOCKER_PASSWORD" ]; then
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

cd integration_tests
docker compose build
docker compose run master
docker compose down --remove-orphans
docker compose -f docker-compose.yml -f kombu.yml run master
docker compose -f docker-compose.yml -f kombu.yml down --remove-orphans
DB=postgres docker compose -f docker-compose.yml -f rdbms.yml run app_test
DB=mysql docker compose -f docker-compose.yml -f rdbms.yml run app_test
docker compose -f docker-compose.yml -f rdbms.yml down --remove-orphans
cd ..

echo "Done!"
