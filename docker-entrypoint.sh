#!/bin/bash
git pull origin master
make $1
make deploy