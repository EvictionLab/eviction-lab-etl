#!/bin/bash
git fetch origin master
git reset --hard FETCH_HEAD
git clean -df
make $1
make deploy