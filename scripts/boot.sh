#!/bin/sh
set -eu
umask 077

# Every container start is a fresh runtime discovery cycle.
# Persistent identity (UUID, REALITY keys, subscription token, short IDs)
# is retained; all deployment-derived artifacts are discarded and regenerated
# from the current Railway deployment environment.
D="${RAILWAY_VOLUME_MOUNT_PATH:-${DATA_DIR:-/data}}"
mkdir -p "$D"

for f in \
  "$D/runtime.json" \
  "$D/state.json" \
  "$D/manifest.json" \
  "$D/runtime-manifest.json" \
  "$D/subscription.txt" \
  "$D/subscription.txt.tmp" \
  "$D/subscription_url.txt" \
  "$D/networking-snapshot.json"; do
  rm -f "$f"
done

# config.json is generated from the freshly discovered runtime. Do not carry
# an old generated Xray config across deployments/networking changes.
rm -f "${XRAY_CONFIG:-$D/config.json}"

PUBLIC_DOMAIN="${RAILWAY_PUBLIC_DOMAIN:-}"
TCP_HOST="${RAILWAY_TCP_PROXY_DOMAIN:-}"
TCP_PORT="${RAILWAY_TCP_PROXY_PORT:-}"
[ -n "$PUBLIC_DOMAIN" ] || { echo "FATAL: RAILWAY_PUBLIC_DOMAIN unavailable" >&2; exit 1; }
[ -n "$TCP_HOST" ] && [ -n "$TCP_PORT" ] || { echo "FATAL: Railway TCP Proxy unavailable" >&2; exit 1; }

cat >"$D/networking-snapshot.json" <<EOF
{
  "source": "current-deployment-environment",
  "authoritative": true,
  "public_domain": "${PUBLIC_DOMAIN}",
  "tcp_proxy_domain": "${TCP_HOST}",
  "tcp_proxy_port": ${TCP_PORT},
  "application_port": 8080
}
EOF
chmod 600 "$D/networking-snapshot.json"

echo "STARTUP_LIFECYCLE=networking-discovery"
echo "RAILWAY_NETWORKING_SOURCE=current-deployment-environment"
echo "RAILWAY_NETWORKING_AUTHORITATIVE=true"
echo "RAILWAY_CURRENT_PUBLIC=$PUBLIC_DOMAIN"
echo "RAILWAY_CURRENT_TCP=$TCP_HOST:$TCP_PORT"
echo "RUNTIME_REGENERATION=required"
echo "SUBSCRIPTION_REGENERATION=required"
echo "ENDPOINT_VALIDATION=required"
echo "XRAY_GATEWAY_START=blocked-until-validation-pass"

exec /opt/xray/scripts/guard.sh
