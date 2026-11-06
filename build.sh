#!/usr/bin/env bash
# Lets Render build from the repository root as well as from the buildexchange folder.
set -o errexit
cd "$(dirname "$0")/buildexchange"
bash build.sh
