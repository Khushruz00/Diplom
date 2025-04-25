#!/bin/bash
export FLASK_APP=Diplom.app
poetry run flask db upgrade
