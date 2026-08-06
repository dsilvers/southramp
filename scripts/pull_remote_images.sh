#!/bin/bash
set -a
source /home/southramp/django/.env
set +a
exec flock -n /tmp/southramp-pull-remote-images.lock \
    timeout 5m /home/southramp/.pyenv/versions/southramp-django/bin/python /home/southramp/django/manage.py pull_remote_images
