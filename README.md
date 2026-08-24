# Railway Xray Gateway

A single-service Railway deployment that provides an Xray gateway, dynamic Railway endpoint discovery, subscription generation, and an optional Cloudflare Tunnel node.

## Repository status

- **Release branch:** `fix-5node-lifecycle-2026-08-24`
- **Runtime model:** 4 Railway base nodes + optional Cloudflare node
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

5. Cloudflare WS TLS, enabled only when the Cloudflare Tunnel configuration is complete.

Railway networking is discovered at runtime. Public domains, TCP proxy hosts/ports, project identifiers, and generated credentials are not hard-coded.

## Deployment

1. Deploy the repository to a Railway project.
2. Add a persistent Volume mounted at `/data`.
3. Create a Railway Public Domain.
4. Create a Railway TCP Proxy targeting internal port `8080`.
5. Redeploy after networking resources are available.
6. Verify `GET /ready` returns HTTP `200` before using the subscription endpoint.

### Cloudflare node

Configure these Railway variables when Node 5 is required:

```text
CLOUDFLARE_TUNNEL_TOKEN
CLOUDFLARE_TUNNEL_ID
CLOUDFLARE_PUBLIC_HOSTNAME
CLOUDFLARE_ORIGIN_SERVICE
WS_PORT
WS_PATH
```

## Runtime invariants

The runtime treats current Railway networking as authoritative. Persistent state is used for identity continuity and change detection, not as an authority for stale endpoints.

The gateway validates the generated subscription against the current runtime before serving it. A valid runtime must expose either 4 or 5 nodes, and the subscription count must match the runtime node count.

The expected subscription order is:

```text
1: railway-xhttp-tls
2: raw-reality-vision
3: xhttp-reality
4: grpc-reality
5: cloudflare-ws-tls (when enabled)
```

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
├── Dockerfile               # Reproducible runtime image
├── railway.toml             # Railway deployment configuration
├── RELEASE-MANIFEST.json    # Release metadata
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
