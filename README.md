# Railway Xray Gateway

A single-service Railway deployment that provides an Xray gateway, dynamic Railway endpoint discovery, subscription generation, and an optional Cloudflare Tunnel node.

## Repository status

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

The public connection to Node 5 is HTTPS/TLS at the Cloudflare hostname. Cloudflare Tunnel forwards the published application to the local XHTTP origin over HTTP. The local Xray Node 5 therefore uses `network=xhttp`, `security=none`; TLS is terminated at the Cloudflare edge.

Railway networking is discovered at runtime. Public domains, TCP proxy hosts/ports, project identifiers, and generated credentials are not hard-coded.

## Deployment

1. Deploy **this release branch** to a Railway project.
2. Add a persistent Volume mounted at `/data`.
3. Create the Railway Public Domain.
4. Create one Railway TCP Proxy targeting internal port `8080`.
5. After creating or changing Railway Networking, **redeploy** so the container discovers the current public domain and TCP Proxy endpoint.
6. Verify `GET /ready` returns HTTP `200` before using the generated subscription.

The application can verify the endpoint values exposed by the current Railway environment, but the actual Railway TCP Proxy target is configured in Railway Networking. The repository therefore records `8080` as the expected target and validates the local gateway listeners; it does not pretend that the target-port setting can be read from an environment variable.

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

`WS_PORT` and `WS_PATH` remain accepted only as legacy aliases for backwards compatibility. New deployments should use the `CLOUDFLARE_XHTTP_*` names.

## Runtime invariants

The runtime treats current Railway networking as authoritative. Persistent state is used for identity continuity and change detection, not as an authority for stale endpoints.

The deployment requires exactly four Railway base nodes and optionally a fifth Cloudflare XHTTP node. The subscription count must match the runtime node count.

The expected subscription order is:

```text
1: railway-xhttp-tls
2: raw-reality-vision
3: xhttp-reality
4: grpc-reality
5: cloudflare-xhttp-tls (when enabled)
```

The same UUID is persisted in `/data/uuid.txt`, so a normal container restart does not silently invalidate an existing subscription.

## Health checks

- `/health` — process-level health response.
- `/ready` — runtime readiness, generated subscription validation, local Xray listener checks, and Cloudflare readiness when enabled.

## Repository layout

```text
.
├── .github/workflows/       # CI/release packaging
├── config/                  # Static runtime inputs
├── scripts/                 # Boot, generation, gateway, guard and runtime logic
├── site/                    # Minimal HTTP landing page
├── Dockerfile               # Reproducible runtime image + build-time invariants
├── railway.toml             # Railway deployment configuration
├── STRUCTURE.md             # Repository structure reference
├── .gitignore               # Local/generated-file exclusions
└── .dockerignore            # Docker build-context exclusions
```

## Release packaging

The GitHub Actions workflow is locked to this release branch. It validates the Node 5 XHTTP definition and the Node 2–4 gateway routes before producing the ZIP and SHA-256 checksum.

## Security

Never commit:

- Cloudflare tunnel tokens
- Private keys
- Generated UUIDs or credentials intended to remain private
- Subscription tokens or URLs containing deployment secrets
- Railway deployment-specific secrets
- Runtime state from `/data`

Use Railway Variables and the persistent `/data` volume for deployment-specific values.
