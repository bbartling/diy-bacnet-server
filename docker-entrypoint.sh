#!/usr/bin/env sh
set -e
# Allow full command override: docker run ... image python3 -m bacpypes_server.main ...
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

name="${BACNET_NAME:-BensServer}"
inst="${BACNET_INSTANCE:-${OFDD_BACNET_DEVICE_INSTANCE:-123456}}"
# bacpypes3 --address, e.g. 192.168.204.18/24:47808 (OT / multi-homed bind)
bind="${BACNET_BIND_ADDRESS:-${OFDD_BACNET_ADDRESS:-}}"

# HTTP: default --public (0.0.0.0:8080). Set BACNET_HTTP_PUBLIC=0|false|no for loopback-only.
pub=""
case "${BACNET_HTTP_PUBLIC:-1}" in
  0|false|no|False|NO) ;;
  *) pub="--public" ;;
esac

if [ -n "$bind" ]; then
  exec python3 -u -m bacpypes_server.main --name "$name" --instance "$inst" --address "$bind" $pub
fi
exec python3 -u -m bacpypes_server.main --name "$name" --instance "$inst" $pub
