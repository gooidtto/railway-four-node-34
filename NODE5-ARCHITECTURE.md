# Node 5 architecture

The repository keeps the original single-service topology.

- Node 1: Railway public domain :443 -> Gateway :8080 -> Xray :10086 (XHTTP + TLS)
- Node 2: shared Railway TCP Proxy -> Gateway :8080 -> SNI `www.cloudflare.com` -> Xray :10087 (TCP + REALITY Vision)
- Node 3: shared Railway TCP Proxy -> Gateway :8080 -> SNI `www.apple.com` -> Xray :10088 (XHTTP + REALITY)
- Node 5: shared Railway TCP Proxy -> Gateway :8080 -> SNI `www.bing.com` -> Xray :10089 (gRPC + REALITY)
- Node 4: unchanged optional Cloudflare Tunnel path

Node 2, Node 3 and Node 5 deliberately share the same Railway TCP Proxy endpoint. The gateway is the only public TCP routing layer and selects the local Xray inbound from the TLS SNI.

Node 5 does not create another Railway TCP Proxy or another service.
