#!/bin/bash
git fetch origin master
git reset --hard FETCH_HEAD
git clean -df

if [ "$1" == "deploy_public_data" ] || [ "$1" == "deploy_data" ]; then
    make $1
elif [ "$1" == "demographics" ]; then
    make -f demographics.mk -j 50 census/00/block-groups.csv census/10/block-groups.csv
    make -f demographics.mk all
    make -f demographics.mk deploy
else
    make $1
    make deploy
fi
