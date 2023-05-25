#!/usr/bin/env bash

set -o errexit  # exit on error

sudo dpkg -l mongodb-database-tools
sudo apt install ./mongodb-database-tools-*-100.7.1.deb

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate