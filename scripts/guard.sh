#!/bin/sh
set -eu

# Runtime-discovered deployment. No project/release/node names are hard-coded.
# Railway networking is authoritative for the current deployment.
PUBLIC_DOMAIN="${RAILWAY_PUBLIC_DOMAIN:-}"
TCP_HOST="${RAILWAY_TCP_PROXY_DOMAIN:-}"
TCP_PORT="${RAILWAY_TCP_PROXY_PORT:-}"
[ -n "$PUBLIC_DOMAIN" ] || { echo "FATAL: RAILWAY_PUBLIC_DOMAIN unavailable" >&2; exit 1; }
[ -n "$TCP_HOST" ] && [ -n "$TCP_PORT" ] || { echo "FATAL: Railway TCP Proxy unavailable" >&2; exit 1; }
case "$TCP_PORT" in ''|*[!0-9]*) echo "FATAL: RAILWAY_TCP_PROXY_PORT must be numeric" >&2; exit 1;; esac
[ "$TCP_PORT" -ge 1 ] && [ "$TCP_PORT" -le 65535 ] || { echo "FATAL: Railway TCP Proxy port out of range" >&2; exit 1; }

# Cloudflare is capability-based: complete configuration enables optional Node 5;
# absent configuration leaves the four-node Railway topology intact. A partial
# configuration is an error rather than a silent, ambiguous deployment.
cf_count=0
for name in CLOUDFLARE_TUNNEL_TOKEN CLOUDFLARE_TUNNEL_ID CLOUDFLARE_PUBLIC_HOSTNAME CLOUDFLARE_ORIGIN_SERVICE CLOUDFLARE_XHTTP_PORT CLOUDFLARE_XHTTP_PATH WS_PORT WS_PATH; do
  eval "value=\${$name:-}"
  [ -n "$value" ] && cf_count=$((cf_count + 1))
done
# Backward compatibility: WS_PORT/WS_PATH are accepted aliases for the
# Cloudflare XHTTP local origin port/path.
CF_PORT="${CLOUDFLARE_XHTTP_PORT:-${WS_PORT:-}}"
CF_PATH="${CLOUDFLARE_XHTTP_PATH:-${WS_PATH:-}}"
BASE_CF_COUNT=0
for name in CLOUDFLARE_TUNNEL_TOKEN CLOUDFLARE_TUNNEL_ID CLOUDFLARE_PUBLIC_HOSTNAME CLOUDFLARE_ORIGIN_SERVICE; do
  eval "value=\${$name:-}"
  [ -n "$value" ] && BASE_CF_COUNT=$((BASE_CF_COUNT + 1))
done
if [ "$BASE_CF_COUNT" -ne 0 ] && [ "$BASE_CF_COUNT" -ne 4 ]; then
  echo "FATAL: incomplete Cloudflare base configuration ($BASE_CF_COUNT/4 variables present)" >&2
  exit 1
fi
if [ "$BASE_CF_COUNT" -eq 4 ]; then
  [ -n "$CF_PORT" ] && [ -n "$CF_PATH" ] || { echo "FATAL: Cloudflare XHTTP port/path required" >&2; exit 1; }
  case "$CF_PORT" in ''|*[!0-9]*) echo "FATAL: Cloudflare XHTTP port must be numeric" >&2; exit 1;; esac
  [ "$CF_PORT" -ge 1 ] && [ "$CF_PORT" -le 65535 ] || { echo "FATAL: Cloudflare XHTTP port out of range" >&2; exit 1; }
  [ "$CF_PORT" != "8080" ] && [ "$CF_PORT" != "10086" ] && [ "$CF_PORT" != "10087" ] && [ "$CF_PORT" != "10088" ] && [ "$CF_PORT" != "10089" ] || { echo "FATAL: Cloudflare XHTTP port conflicts with an internal port" >&2; exit 1; }
  case "$CF_PATH" in /*) ;; *) echo "FATAL: Cloudflare XHTTP path must start with /" >&2; exit 1;; esac
fi

export NODE_MODE="${NODE_MODE:-auto}"
export EXPECTED_NODES="${EXPECTED_NODES:-auto}"

python3 /opt/xray/scripts/runtime-manifest.py

echo "PRODUCTION_GUARD=PASS"
echo "NODE_MODE=$NODE_MODE"
echo "EXPECTED_NODES=$EXPECTED_NODES"
echo "RAILWAY_PUBLIC_DOMAIN=$PUBLIC_DOMAIN"
echo "RAILWAY_TCP_PROXY=$TCP_HOST:$TCP_PORT"
[ "$BASE_CF_COUNT" -eq 4 ] && echo "CLOUDFLARE_CAPABILITY=enabled" || echo "CLOUDFLARE_CAPABILITY=disabled"
[ "$BASE_CF_COUNT" -eq 4 ] && echo "CLOUDFLARE_TRANSPORT=XHTTP_TLS"
exec /opt/xray/scripts/start.sh
