#!/bin/bash

# Sets the environmental variables in `.env` and configures aws
# Provides a quick way to configure when using the docker container
# Should be run as `. init.sh` or `source init.sh` so the environment
# variables are set in the active shell session.
#
# See `.env.staging` or .env.production` for sample `.env` files.

cd /App
export $(grep -v '^#' .env | xargs)
aws configure set aws_access_key_id $AWS_ACCESS_ID
aws configure set aws_secret_access_key $AWS_SECRET_KEY
aws configure set default.region us-east-1
