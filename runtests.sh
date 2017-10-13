#!/bin/sh

python -m unittest discover --start-directory search/tests --top-level-directory .

python django_testapp/manage.py test search.django
