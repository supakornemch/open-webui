#!/bin/sh
set -eu

nginx -t
nginx
exec docker/prod_entrypoint.sh "$@"