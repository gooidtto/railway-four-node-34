import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
generate = (ROOT / "scripts/generate.py").read_text()
gateway = (ROOT / "scripts/gateway.py").read_text()
start = (ROOT / "scripts/start.sh").read_text()
dockerfile = (ROOT / "Dockerfile").read_text()

def test_node5_ports_and_route():
    assert '10089' in generate
    assert 'GRPC_SNI' in generate
    assert 'www.bing.com' in generate
    assert 'grpcSettings' in generate
    assert 'serviceName' in generate
    assert '10089' in gateway
    assert 'www.bing.com' in gateway
    assert '10089' in start
    assert '10089' in dockerfile

def test_shared_tcp_proxy():
    assert 'TCP_HOST' in generate and 'TCP_PORT' in generate
    grpc_block = re.search(r'"type": "grpc".*?GRPC_SERVICE_NAME', generate, re.S)
    assert grpc_block

def test_cloudflare_port_excludes_node5():
    assert '10086, 10087, 10088, 10089' in generate

def test_runtime_supports_four_or_five_nodes():
    assert 'NODE_COUNT not in (4, 5)' in generate
    assert 'n in (4, 5)' in gateway
    assert 'expected not in (4, 5)' in gateway
