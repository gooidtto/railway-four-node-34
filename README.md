# Railway Xray Gateway

A single-service Railway deployment that provides an Xray gateway, dynamic Railway endpoint discovery, subscription generation, and an optional Cloudflare Tunnel node.

## Release baseline

- **Release branch:** `release-5node-xhttp-cloudflare-v3-2026-08-24`
- **Runtime model:** 4 Railway base nodes + optional Cloudflare XHTTP node
- **Persistent state:** `/data`
- **Gateway:** `8080`
- **Readiness:** `/ready`

## Architecture

### Base nodes

1. Railway XHTTP TLS
2. RAW REALITY Vision
3. XHTTP REALITY
4. gRPC REALITY

### Optional node

5. **Cloudflare XHTTP TLS**, enabled only when the Cloudflare Tunnel configuration is complete.

The public connection to Node 5 is HTTPS/TLS at the Cloudflare hostname. Cloudflare Tunnel forwards the published application to the local XHTTP origin over HTTP. The local Xray Node 5 therefore uses `network=xhttp`, `security=none`; public TLS is terminated at Cloudflare.

Railway networking is discovered at runtime. Public domains, TCP proxy hosts/ports, project identifiers, and generated credentials are not hard-coded.

## Deployment

1. Deploy **this release branch** to a Railway project.
2. Add a persistent Volume mounted at `/data`.
3. Create the Railway Public Domain.
4. Create a Railway TCP Proxy whose **target port is `8080`**.
5. After changing or recreating Railway Networking, **redeploy the service** so the new environment values are authoritative.
6. Confirm the startup log reports `RAILWAY_NETWORKING_SOURCE=current-deployment-environment` and `RAILWAY_TCP_PROXY_EXPECTED_TARGET=8080`.
7. Verify `GET /ready` returns HTTP `200` before using the subscription endpoint.

### Cloudflare node

Configure these Railway variables when Node 5 is required:

```text
CLOUDFLARE_TUNNEL_TOKEN
CLOUDFLARE_TUNNEL_ID
CLOUDFLARE_PUBLIC_HOSTNAME
CLOUDFLARE_ORIGIN_SERVICE
CLOUDFLARE_XHTTP_PORT
CLOUDFLARE_XHTTP_PATH
```

The older `WS_PORT` / `WS_PATH` names are accepted only as compatibility fallbacks. New deployments should use the explicit `CLOUDFLARE_XHTTP_*` names.

The Cloudflare published application should map the public hostname to the local HTTP XHTTP origin represented by `CLOUDFLARE_ORIGIN_SERVICE` and `CLOUDFLARE_XHTTP_PORT`, using `CLOUDFLARE_XHTTP_PATH`. The public hostname remains HTTPS while the local origin is HTTP.

## Runtime invariants

The runtime treats current Railway networking as authoritative. Persistent `/data` state is used for identity continuity and change detection, not as an authority for stale endpoints.

At every startup:

```text
current Railway Networking
        ↓
runtime generation
        ↓
subscription generation
        ↓
endpoint / UUID / node-count validation
        ↓
Xray configuration test
        ↓
local listener readiness
        ↓
Gateway
```

A valid runtime must expose either 4 or 5 nodes, and the subscription count must match the runtime node count.

The expected subscription order is:

```text
1: railway-xhttp-tls
2: raw-reality-vision
3: xhttp-reality
4: grpc-reality
5: cloudflare-xhttp-tls (when enabled)
```

Node 2, Node 3, and Node 4 intentionally share the current Railway TCP Proxy endpoint. The Gateway on `8080` routes their TLS SNI to `10087`, `10088`, and `10089` respectively.

## Health checks

- `/health` — process-level health response.
- `/ready` — generated subscription validation, local Xray listener checks, and Cloudflare readiness when enabled.

## Repository layout

```text
.
├── .github/workflows/       # CI/release packaging
├── config/                  # Static runtime inputs
├── scripts/                 # Boot, generation, gateway and runtime logic
├── site/                    # Minimal HTTP landing page
├── Dockerfile               # Reproducible runtime image
├── railway.toml             # Railway deployment configuration
├── STRUCTURE.md             # Repository structure reference
├── .gitignore               # Local/generated-file exclusions
└── .dockerignore            # Docker build-context exclusions
```

## Release packaging

The repository includes a GitHub Actions workflow that creates a ZIP archive and SHA-256 checksum for the release branch. Release archives are build artifacts and are intentionally excluded from Git tracking.

## Security

Never commit:

- Cloudflare tunnel tokens
- Private keys
- Generated UUIDs or credentials intended to remain private
- Subscription tokens or URLs containing deployment secrets
- Railway deployment-specific secrets
- Runtime state from `/data`

Use Railway Variables and the persistent `/data` volume for deployment-specific values.
