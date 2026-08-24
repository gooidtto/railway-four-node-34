# Railway Xray Gateway

Dynamic single-service Railway deployment with an Xray gateway and optional Cloudflare WS node.

## Architecture

- Railway service: `8080`
- Persistent volume: `/data`
- Public Domain + TCP Proxy
- 3 base nodes
- Optional 4th node through Cloudflare Tunnel
- Health endpoint: `/ready`

Railway networking is discovered at runtime. Project names, domains, ports, and node display names are not hard-coded.

## Deploy

1. Deploy this repository to a new Railway project.
2. Add a Volume mounted at `/data`.
3. Create a Public Domain.
4. Create a TCP Proxy targeting internal port `8080`.
5. Redeploy.

For Node 4, configure:

```text
CLOUDFLARE_TUNNEL_TOKEN
CLOUDFLARE_TUNNEL_ID
CLOUDFLARE_PUBLIC_HOSTNAME
CLOUDFLARE_ORIGIN_SERVICE
WS_PORT
WS_PATH
```

The runtime generates the current project's nodes and subscription from the Railway environment and available capabilities.

## Runtime

Persistent identity is stored under `/data`. Current Railway networking is always authoritative; previous runtime state is used only for continuity and change detection.

## Security

Keep tokens, private keys, generated credentials, subscription URLs, and deployment-specific values out of Git. Use Railway variables and the `/data` volume.
