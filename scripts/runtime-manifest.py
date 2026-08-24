#!/usr/bin/env python3
"""Generate deployment metadata from the current Railway runtime environment."""
import hashlib
import json
import os
from pathlib import Path

D = Path(os.environ.get("DATA_DIR", "/data"))
D.mkdir(parents=True, exist_ok=True)
public = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
tcp_host = os.environ.get("RAILWAY_TCP_PROXY_DOMAIN", "").strip()
tcp_port = os.environ.get("RAILWAY_TCP_PROXY_PORT", "").strip()
cf_names = ("CLOUDFLARE_TUNNEL_TOKEN", "CLOUDFLARE_TUNNEL_ID", "CLOUDFLARE_PUBLIC_HOSTNAME", "CLOUDFLARE_ORIGIN_SERVICE", "CLOUDFLARE_XHTTP_PORT", "CLOUDFLARE_XHTTP_PATH")
cf = {k: os.environ.get(k, "").strip() for k in cf_names}
cf_port = cf["CLOUDFLARE_XHTTP_PORT"] or os.environ.get("WS_PORT", "").strip()
cf_path = cf["CLOUDFLARE_XHTTP_PATH"] or os.environ.get("WS_PATH", "").strip()
cf_enabled = all(bool(cf[k]) for k in cf_names[:4]) and bool(cf_port) and bool(cf_path)

nodes = []
if public:
    nodes.append({"id":"node-01","name":os.environ.get("NODE_01_NAME","Node 01").strip() or "Node 01","transport":"xhttp","security":"tls","endpoint_source":"railway_public_domain","endpoint":f"{public}:443"})
if tcp_host and tcp_port:
    raw_sni=os.environ.get("REALITY_RAW_SNI","www.cloudflare.com").strip(); xhttp_sni=os.environ.get("REALITY_XHTTP_SNI","www.apple.com").strip(); grpc_sni=os.environ.get("REALITY_GRPC_SNI","www.bing.com").strip(); endpoint=f"{tcp_host}:{tcp_port}"
    nodes.extend([
        {"id":"node-02","name":os.environ.get("NODE_02_NAME","Node 02").strip() or "Node 02","transport":"tcp","security":"reality","flow":"xtls-rprx-vision","sni":raw_sni,"endpoint_source":"railway_tcp_proxy","endpoint":endpoint},
        {"id":"node-03","name":os.environ.get("NODE_03_NAME","Node 03").strip() or "Node 03","transport":"xhttp","security":"reality","sni":xhttp_sni,"endpoint_source":"railway_tcp_proxy","endpoint":endpoint},
        {"id":"node-04","name":os.environ.get("NODE_04_NAME","Node 04").strip() or "Node 04","transport":"grpc","security":"reality","sni":grpc_sni,"endpoint_source":"railway_tcp_proxy","endpoint":endpoint},
    ])
if cf_enabled:
    nodes.append({"id":"node-05","name":os.environ.get("NODE_05_NAME","Node 05").strip() or "Node 05","transport":"xhttp","security":"tls","endpoint_source":"cloudflare_tunnel","endpoint":f"{cf['CLOUDFLARE_PUBLIC_HOSTNAME']}:443","path":cf_path,"origin_protocol":"http"})

if len(nodes) not in (4, 5):
    raise SystemExit(f"FATAL: expected 4 Railway nodes or 5 with Cloudflare, discovered {len(nodes)}")
if not public or not tcp_host or not tcp_port:
    raise SystemExit("FATAL: current Railway public domain and TCP proxy are required")

policy={"node_count":len(nodes),"base_nodes":4,"cloudflare_configured":cf_enabled,"cloudflare_transport":"xhttp","networking_source":"current-deployment-environment","networking_authoritative":True,"endpoints_source":"current-railway-environment","gateway_application_port":8080,"tcp_proxy_expected_target":8080}
manifest={"schema":3,"kind":"runtime-deployment-manifest","project":{"name":os.environ.get("PROJECT_NAME","").strip() or None,"release":os.environ.get("RELEASE_NAME","").strip() or "fix-5node-xhttp-cloudflare-v3"},"policy":policy,"nodes":nodes,"capabilities":{"single_gateway":True,"sni_routing":True,"dynamic_railway_networking":True,"subscription_generation":True,"uuid_invariant":True,"cloudflare_tunnel":cf_enabled,"cloudflare_xhttp":cf_enabled},"railway_networking":{"public_domain":public,"tcp_proxy_domain":tcp_host,"tcp_proxy_port":tcp_port,"application_port":8080,"expected_tcp_proxy_target":8080}}
manifest["fingerprint"]=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()
(D/"runtime-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(f"RUNTIME_NODE_COUNT={len(nodes)}"); print("RUNTIME_BASE_NODE_COUNT=4"); print(f"RUNTIME_CLOUDFLARE={'enabled' if cf_enabled else 'disabled'}"); print(f"RUNTIME_CLOUDFLARE_TRANSPORT={'xhttp' if cf_enabled else 'disabled'}"); print("RAILWAY_TCP_PROXY_EXPECTED_TARGET=8080"); print(f"RUNTIME_MANIFEST={D/'runtime-manifest.json'}"); print(f"RUNTIME_MANIFEST_FINGERPRINT={manifest['fingerprint']}")
for n in nodes: print(f"NODE_DISCOVERED={n['id']} name={n['name']} transport={n['transport']} security={n['security']} endpoint={n['endpoint']}")
