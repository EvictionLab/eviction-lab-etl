#!/bin/bash
git pull origin master
exec "$@"
make deploy