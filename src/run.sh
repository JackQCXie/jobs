#!/bin/bash

today=$(date +%Y%m%d)
locations=("vancouver" "toronto" "montreal" "ottowa" "edmonton" "calgary")  # Add as many as you want

for location in "${locations[@]}"; do

    # kill screen if already exists
    if screen -list | grep -q "\.${location}[[:space:]]"; then
        screen -S "$location" -X quit
    fi

    # run python script in a new screen session, auto-closing when done
    screen -dmS "$location" bash -c "python3 -u get_jobposts.py -l $location 2>&1 | tee ../log/$today-$location.log"

done