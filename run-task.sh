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

if [[ ( -z "${AWS_ACCESS_ID}" ) && ( $1 != config ) ]]; then
    # running on AWS batch, get master from source control
    git fetch origin master
    git reset --hard FETCH_HEAD
    git clean -df
else
    # running locally in docker container, configure aws
    if [[ -z "${AWS_ACCESS_ID}" ]]; then
        printf '%s\n' "Missing AWS_ACCESS_ID environment variable, could not configure AWS CLI." >&2
    elif [[ -z "${AWS_SECRET_KEY}" ]]; then
        printf '%s\n' "Missing AWS_SECRET_KEY environment variable, could not configure AWS CLI." >&2
    else
        aws configure set aws_access_key_id $AWS_ACCESS_ID
        aws configure set aws_secret_access_key $AWS_SECRET_KEY
        aws configure set default.region us-east-1
        printf '%s\n' "AWS configured."
    fi
fi

if [[ $1 == deploy_public_data ]] || [[ $1 == deploy_app_data ]]; then
    # job is a deploy
    make -f create_eviction_data.mk $1
elif [[ $1 == *census* ]]; then
    # job is to create census geography
    make -f fetch_census_geography.mk $1
    make -f fetch_census_geography.mk deploy
elif [[ $1 == *data/demographics/raw* ]]; then
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
elif [[ $1 == *data/demographics* ]]; then
    # job is to process and crosswalk demographics
    make -f process_demographics.mk $1
    make -f process_demographics.mk deploy_logs
    make -f process_demographics.mk deploy
elif [[ $1 == *data* ]]; then
    # job is to merge eviction and demographic data
    make -f create_eviction_data.mk $1
    make -f create_eviction_data.mk deploy_logs
    make -f create_eviction_data.mk deploy
elif [[ $1 == *tiles* ]]; then
    # job is to create and deploy tilesets
    make -f create_eviction_tilesets.mk $1
    make -f create_eviction_tilesets.mk deploy
else
    if [[ $1 != config ]]; then
        printf '%s\n' "Invalid target for submit jobs." >&2
        exit 1
    fi
fi
exit
