# syntax=docker/dockerfile:1
ARG XRAY_VERSION=26.3.27
ARG CLOUDFLARED_VERSION=2026.7.3
FROM ghcr.io/xtls/xray-core:${XRAY_VERSION} AS xray
FROM cloudflare/cloudflared:${CLOUDFLARED_VERSION} AS cloudflared
FROM python:3.12-alpine3.22
ARG XRAY_VERSION
ARG CLOUDFLARED_VERSION
ENV XRAY_VERSION=${XRAY_VERSION} CLOUDFLARED_VERSION=${CLOUDFLARED_VERSION} PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apk add --no-cache openssl ca-certificates && mkdir -p /etc/xray /data /opt/xray/scripts /opt/xray/config /opt/xray/site
COPY --from=xray /usr/local/bin/xray /usr/local/bin/xray
COPY --from=cloudflared /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY scripts/ /opt/xray/scripts/
COPY config/ /opt/xray/config/
COPY site/ /opt/xray/site/
RUN sed -i \
    -e 's/import socket/import socket\\nimport sys/' \
    -e 's/logging.basicConfig(level=/logging.basicConfig(stream=sys.stdout, level=/' \
    -e 's/log\\.warning("TCP_ACCEPT/log.info("TCP_ACCEPT/' \
    -e 's/log\\.warning("ROUTE_SELECTED/log.info("ROUTE_SELECTED/' \
    -e 's/log\\.warning("UPSTREAM_CONNECT_OK/log.info("UPSTREAM_CONNECT_OK/' \
    -e 's/log\\.warning("INITIAL_FORWARDED/log.debug("INITIAL_FORWARDED/' \
    -e 's/log\\.warning("SUBSCRIPTION_HTTP_RENDER=PASS/log.info("SUBSCRIPTION_HTTP_RENDER=PASS/' \
    /opt/xray/scripts/gateway.py && \
    sed -i 's/BUILD_ID="fix-5node-lifecycle-v2"/BUILD_ID="fix-5node-lifecycle-v3"/; s/SOURCE_BUILD="fix-5node-lifecycle-v1"/SOURCE_BUILD="fix-5node-lifecycle-v2"/' /opt/xray/scripts/start.sh && \
    sed -i 's/print("NODE_ORDER=1:railway-xhttp-tls,2:raw-reality-vision,3:xhttp-reality,4:grpc-reality,5:cloudflare-ws-tls",flush=True)/print(f"RAILWAY_BASE_NODES=4",flush=True); print("SUBSCRIPTION_NODE_ORDER=1:railway-xhttp-tls,2:raw-reality-vision,3:xhttp-reality,4:grpc-reality" + (",5:cloudflare-ws-tls" if CF_ENABLED else ""),flush=True)/' /opt/xray/scripts/generate.py && \
    chmod 0755 /usr/local/bin/xray /usr/local/bin/cloudflared /opt/xray/scripts/*.sh /opt/xray/scripts/*.py && chmod 0644 /opt/xray/config/* /opt/xray/site/*
ENV BUILD_ID=fix-5node-lifecycle-v3 \
    SOURCE_BUILD=fix-5node-lifecycle-v2 \
    NODE_MODE=auto \
    EXPECTED_NODES=auto \
    PORT=8080 \
    GATEWAY_PORT=8080 \
    XRAY_CONFIG=/etc/xray/config.json \
    DATA_DIR=/data \
    REALITY_RAW_SNI=www.cloudflare.com \
    REALITY_RAW_TARGET=www.cloudflare.com:443 \
    REALITY_FINGERPRINT=chrome \
    REALITY_XHTTP_SNI=www.apple.com \
    REALITY_XHTTP_TARGET=www.apple.com:443 \
    REALITY_GRPC_SNI=www.bing.com \
    REALITY_GRPC_TARGET=www.bing.com:443 \
    GRPC_SERVICE_NAME=grpc-service \
    XHTTP_PATH=/xhttp \
    READY_TIMEOUT=90 \
    CLOUDFLARE_READY_TIMEOUT=45 \
    GATEWAY_MAX_CONNECTIONS=512 \
    GATEWAY_READ_TIMEOUT=20 \
    GATEWAY_UPSTREAM_TIMEOUT=10 \
    GATEWAY_IDLE_TIMEOUT=900 \
    GATEWAY_MAX_INITIAL=131072 \
    GATEWAY_LOGLEVEL=INFO
RUN echo "SOURCE_BUILD=${SOURCE_BUILD} BUILD_ID=${BUILD_ID}"
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/ready', timeout=8).read()"
WORKDIR /opt/xray
ENTRYPOINT ["/opt/xray/scripts/boot.sh"]
