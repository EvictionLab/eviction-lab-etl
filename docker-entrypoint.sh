#!/bin/bash
git fetch origin master
git reset --hard FETCH_HEAD
git clean -df

if [[ $1 == deploy_public_data ]] || [[ $1 == deploy_data ]]; then
    # if it's a deploy task for the main makefile, deploy and exit
    make $1
elif [[ $1 == *demographics* ]]; then
    # if building block groups, get the census data first and run 10 jobs at a time
    if [[ $1 == *block-groups-00* ]]; then
        make -f demographics.mk -j 10 census/00/block-groups.csv
    elif [[ $1 == *block-groups-10* ]]; then
        make -f demographics.mk -j 10 census/10/block-groups.csv
    elif [[ $1 == *block-groups* ]]; then
        make -f demographics.mk -j 10 census/00/block-groups.csv census/10/block-groups.csv
    fi
    # perform requested demographic task
    make -f demographics.mk $1
    make -f demographics.mk deploy_logs
    if [[ $1 == *raw* ]]; then
        make -f demographics.mk deploy_raw
    else
        make -f demographics.mk deploy
    fi
else
    make $1
    make deploy
    # deploy the generated validation data
    make deploy_validation_data
fi
