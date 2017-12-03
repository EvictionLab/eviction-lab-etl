#!/bin/bash
git fetch origin master
git reset --hard FETCH_HEAD
git clean -df
if [ "$1" != "deploy_data" ] ; then make $1 && make deploy; else make $1; fi