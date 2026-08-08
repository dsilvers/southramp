#!/bin/bash
set -a
source /home/southramp/django/.env
set +a
exec /home/southramp/.pyenv/versions/southramp-django/bin/python /home/southramp/django/manage.py delete_old_images --hours 1
