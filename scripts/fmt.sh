#!/bin/bash

DIR=`dirname $0`

# Format the project.

black -l 79 \
    $DIR/../setup.py \
    $DIR/../ipinfo \
    $DIR/../tests
