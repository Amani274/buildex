#!/usr/bin/env bash
set -o errexit
cd "$(dirname "$0")/buildexchange"
exec bash start.sh
