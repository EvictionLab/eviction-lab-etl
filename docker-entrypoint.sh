#!/bin/bash
git fetch origin master
git reset --hard FETCH_HEAD
git clean -df

if [[ $1 == deploy_public_data ]] || [[ $1 == deploy_data ]]; then
    make $1
elif [[ $1 == *demographics* ]]; then
    if [[ $1 == *block-groups* ]]; then
        make -f demographics.mk -j 10 census/00/block-groups.csv census/10/block-groups.csv
    fi
    make -f demographics.mk $1
    make -f demographics.mk deploy_logs
    make -f demographics.mk deploy
else
    make $1
    make deploy
    make deploy_validation_data
fi
