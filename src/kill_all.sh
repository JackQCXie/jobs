#!/bin/bash

# kill all screens
for session in $(screen -ls | awk '/[0-9]+\./ {print $1}'); do
    screen -S "${session}" -X quit
done