#!/bin/bash
# Pulls main and restarts the app. Run as the southramp user — by hand, or
# via the GitHub Actions deploy key (forced command in authorized_keys).
set -euo pipefail

APP=/home/southramp/django
PY=/home/southramp/.pyenv/versions/southramp-django/bin/python

exec 9>/tmp/southramp-deploy.lock
flock -n 9 || { echo "deploy already running"; exit 1; }

cd "$APP"
set -a
source .env
set +a

git fetch --quiet origin main
git merge --ff-only origin/main
echo "deploying $(git log --oneline -1)"

"$PY" -m pip install --quiet -r requirements.txt
"$PY" manage.py migrate --noinput
"$PY" manage.py collectstatic --noinput --verbosity 0

sudo -n /usr/bin/systemctl restart southramp-django
sudo -n /usr/bin/systemctl restart southramp-ftp
echo "deployed"
