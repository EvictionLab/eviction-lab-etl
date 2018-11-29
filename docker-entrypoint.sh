#!/bin/bash

# Docker entry point that recieves a filename to build,
# triggered on AWS batch by `utils/submit_jobs.py`.
#
# e.g. `python3 utils/submit_jobs.py data/demographics/block-groups.csv`
#   will start a docker container in AWS batch and run this script with
#   $1 = data/demographics/block-groups.csv
#
# This script determines which makefile is used to make the requested
# file, and also deploys it if needed.

git fetch origin master
git reset --hard FETCH_HEAD
git clean -df

if [[ $1 == deploy_public_data ]] || [[ $1 == deploy_data ]]; then
    # job is a deploy
    make $1
elif [[ $1 == *demographics/raw* ]]; then
    # job is to fetch demographics from census api
    # if building block groups, get the census data first and run 10 jobs at a time
    if [[ $1 == *block-groups-00* ]]; then
        make -f fetch_raw_census_api.mk -j 10 census/00/block-groups.csv
    elif [[ $1 == *block-groups-10* ]]; then
        make -f fetch_raw_census_api.mk -j 10 census/10/block-groups.csv
    fi
    # fetch the requested data then deploy the logs and data to S3
    make -f fetch_raw_census_api.mk $1
    make -f fetch_raw_census_api.mk deploy_logs
    make -f fetch_raw_census_api.mk deploy
elif [[ $1 == *demographics* ]]; then
    # job is to process demographics, fetch from S3 for the provided fetch date
    make -f fetch_raw_s3.mk DATE=2018-11-28
    make -f process_demographics.mk $1
    make -f process_demographics.mk deploy_logs
    make -f process_demographics.mk deploy
else
    # job is a non-deploy and non-demographics task
    make $1
    make deploy
    # deploy the generated validation data
    make deploy_validation_data
fi
