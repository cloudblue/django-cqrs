#!/bin/bash

set -e

if [ "$COMPAT_TESTS" == "yes" ]; then
    echo "Running backward compatibility tests....."
    cd integration_tests 
	docker-compose -f docker-compose.yml -f masterV1.yml build
	docker-compose -f docker-compose.yml -f masterV1.yml run master
	docker-compose -f docker-compose.yml -f masterV1.yml down --remove-orphans

	docker-compose -f docker-compose.yml -f replicaV1.yml build
	docker-compose -f docker-compose.yml -f replicaV1.yml run master
	docker-compose -f docker-compose.yml -f replicaV1.yml down --remove-orphans
    cd ..
    echo "Done!"
else
    echo "Skip backward compatibility tests..."
fi
