#!/bin/bash

location=toronto
today=$(date +%Y%m%d)

python3 -u get_jobposts.py -l $location 2>&1 | tee ../log/$today-$location.log