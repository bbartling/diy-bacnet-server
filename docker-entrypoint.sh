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
# Normalize like Python env parsing: trim whitespace, lowercase, then match disable literals only.
pub=""
_hp_raw="${BACNET_HTTP_PUBLIC:-1}"
_hp=$(printf '%s' "$_hp_raw" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | tr '[:upper:]' '[:lower:]')
[ -z "$_hp" ] && _hp="1"
case "$_hp" in
  0|false|no) ;;
  *) pub="--public" ;;
esac

if [ -n "$bind" ]; then
  exec python3 -u -m bacpypes_server.main --name "$name" --instance "$inst" --address "$bind" $pub
fi
exec python3 -u -m bacpypes_server.main --name "$name" --instance "$inst" $pub
