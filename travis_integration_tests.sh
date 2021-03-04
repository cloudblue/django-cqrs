#!/bin/bash

set -e

if [ "$INTEGRATION_TESTS" == "yes" ]; then
    echo "Running integration tests....."
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
    cd integration_tests
    docker-compose build
    docker-compose run master
    docker-compose down --remove-orphans
    docker-compose -f docker-compose.yml -f kombu.yml run master
	docker-compose -f docker-compose.yml -f kombu.yml down --remove-orphans
    cd ..
    echo "Done!"
else
    echo "Skip integration tests..."
fi
