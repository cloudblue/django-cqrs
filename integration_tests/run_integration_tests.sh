#!/bin/bash


echo "####################################################"
echo " Running tests:                                     "
echo
echo "   -> transport: $CQRS_MASTER_TRANSPORT             "
echo "   -> url: $CQRS_BROKER_URL                         "
echo
echo "####################################################"

sleep 12

pytest integration_tests/
