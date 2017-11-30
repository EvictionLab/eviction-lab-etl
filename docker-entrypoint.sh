#!/bin/bash
git fetch origin master
git reset --hard FETCH_HEAD
git clean -df
make $1
if [ "$1" != "deploy_data" ] ; then make deploy; fi