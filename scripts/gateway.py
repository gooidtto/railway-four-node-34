#!/usr/bin/env python3
import asyncio, base64, json, logging, os, re, socket, struct, urllib.parse
from pathlib import Path

PORT=int(os.environ.get("GATEWAY_PORT","8080"))
D=Path(os.environ.get("DATA_DIR","/data")); SITE=Path("/opt/xray/site/index.html")
TOKEN=D/"subscription_token.txt"; SUB=D/"subscription.txt"; RUNTIME=D/"runtime.json"
HTTP_DEST=("127.0.0.1",10086)
RAW_SNI=os.environ.get("REALITY_RAW_SNI","www.cloudflare.com").strip().lower().rstrip(".")
XHTTP_SNI=os.environ.get("REALITY_XHTTP_SNI","www.apple.com").strip().lower().rstrip(".")
GRPC_SNI=os.environ.get("REALITY_GRPC_SNI","www.bing.com").strip().lower().rstrip(".")
ROUTES={RAW_SNI:("127.0.0.1",10087,"raw-reality-vision"),XHTTP_SNI:("127.0.0.1",10088,"xhttp-reality"),GRPC_SNI:("127.0.0.1",10089,"grpc-reality")}
MAX_CONNECTIONS=max(16,int(os.environ.get("GATEWAY_MAX_CONNECTIONS","512")))
INITIAL_TIMEOUT=max(2,float(os.environ.get("GATEWAY_READ_TIMEOUT","20")))
UPSTREAM_TIMEOUT=max(2,float(os.environ.get("GATEWAY_UPSTREAM_TIMEOUT","10")))
IDLE_TIMEOUT=max(30,float(os.environ.get("GATEWAY_IDLE_TIMEOUT","900")))
MAX_INITIAL=min(262144,max(4096,int(os.environ.get("GATEWAY_MAX_INITIAL","131072"))))
SEM=asyncio.Semaphore(MAX_CONNECTIONS)
HTTP_METHODS=(b"GET ",b"POST ",b"HEAD ",b"PUT ",b"OPTIONS ",b"PATCH ",b"DELETE ",b"PRI * HTTP/2.0")
logging.basicConfig(level=getattr(logging,os.environ.get("GATEWAY_LOGLEVEL","INFO").upper(),logging.INFO),format="[gateway] %(levelname)s %(message)s")
log=logging.getLogger("gateway")

def runtime():
    try:return json.loads(RUNTIME.read_text())
    except Exception:return {}
def expected_nodes():
    n=runtime().get("nodes",{}).get("count",0)
    try:n=int(n)
    except Exception:n=0
    return n if n in (4,5) else 0
def port_ready(p):
    try:
        s=socket.create_connection(("127.0.0.1",p),1.5);s.close();return True
    except OSError:return False
def cf_ready():
    if not runtime().get("cloudflare",{}).get("enabled"): return True
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:2000/ready",timeout=2).read();return True
    except Exception:return False
def readiness():
    n=expected_nodes()
    if n not in (4,5) or not RUNTIME.exists() or not SUB.exists() or not TOKEN.exists(): return False,"state"
    lines=[x.strip() for x in SUB.read_text().splitlines() if x.strip()]
    if len(lines)!=n or any(not x.startswith("vless://") for x in lines): return False,"subscription"
    for p,label in ((10086,"xhttp-http"),(10087,"raw-reality"),(10088,"xhttp-reality"),(10089,"grpc-reality")):
        if not port_ready(p):return False,label
    if not cf_ready():return False,"cloudflare"
    return True,"ready"

def endpoint_state():
    r=runtime(); tcp=r.get("tcp_proxy",{}) or {}; cf=r.get("cloudflare",{}) or {}
    try:tp=int(tcp.get("port",0))
    except Exception:tp=0
    return (str(r.get("public_domain","")).strip().lower().rstrip("."),str(tcp.get("domain","")).strip().lower().rstrip("."),tp,str(cf.get("public_hostname","")).strip().lower().rstrip("."))

def rewrite(line,host,port,sni=None):
    u=urllib.parse.urlsplit(line)
    if u.scheme!="vless" or not u.username or not host:return line
    q=urllib.parse.parse_qsl(u.query,keep_blank_values=True)
    if sni:q=[(k,sni if k=="sni" else v) for k,v in q]
    return urllib.parse.urlunsplit(("vless",f"{u.username}@{host}:{port}",u.path,urllib.parse.urlencode(q),u.fragment))

def fresh_subscription():
    if not SUB.exists() or not RUNTIME.exists():return None,"STATE_MISSING"
    lines=[x.strip() for x in SUB.read_text().splitlines() if x.strip()];n=expected_nodes()
    if n not in (4,5) or len(lines)!=n or any(not x.startswith("vless://") for x in lines):return None,"SUB_INVALID"
    public,tcp_host,tcp_port,cf_host=endpoint_state()
    if not public or not tcp_host or not tcp_port:return None,"NETWORKING_INVALID"
    lines[0]=rewrite(lines[0],public,443,public)
    for i in (1,2,3):lines[i]=rewrite(lines[i],tcp_host,tcp_port)
    if n==5:
        if not cf_host:return None,"CLOUDFLARE_HOST_INVALID"
        lines[4]=rewrite(lines[4],cf_host,443,cf_host)
    if not re.match(rf"^vless://[^@]+@{re.escape(public)}:443\?",lines[0]):return None,"NODE1_HTTP_ENDPOINT_MISMATCH"
    for i in (1,2,3):
        if not re.match(rf"^vless://[^@]+@{re.escape(tcp_host)}:{tcp_port}\?",lines[i]):return None,f"NODE{i+1}_HTTP_ENDPOINT_MISMATCH"
    if n==5 and not re.match(rf"^vless://[^@]+@{re.escape(cf_host)}:443\?",lines[4]):return None,"NODE5_HTTP_ENDPOINT_MISMATCH"
    return lines,"OK"

def subscription(token):
    if not TOKEN.exists() or token!=TOKEN.read_text().strip():return None,"TOKEN_INVALID"
    lines,status=fresh_subscription()
    if lines is None:return None,status
    public,tcp_host,tcp_port,cf_host=endpoint_state()
    log.info("SUBSCRIPTION_HTTP_RENDER=PASS public=%s tcp=%s:%s nodes=%d",public,tcp_host,tcp_port,len(lines))
    return base64.b64encode("\n".join(lines).encode()),"OK"

def parse_sni(h):
    try:
        if len(h)<4 or h[0]!=1:return None
        L=int.from_bytes(h[1:4],"big");end=4+L;p=38
        if p>=end:return None
        p+=1+h[p]
        if p+2>end:return None
        cl=struct.unpack("!H",h[p:p+2])[0];p+=2+cl
        if p>=end:return None
        p+=1+h[p]
        if p+2>end:return None
        el=struct.unpack("!H",h[p:p+2])[0];p+=2;ee=p+el
        while p+4<=ee:
            typ,ln=struct.unpack("!HH",h[p:p+4]);p+=4
            if p+ln>ee:return None
            if typ==0 and ln>=5:
                q=p+2;stop=p+ln
                while q+3<=stop:
                    nt=h[q];nl=struct.unpack("!H",h[q+1:q+3])[0];q+=3
                    if q+nl>stop:return None
                    if nt==0:return h[q:q+nl].decode("idna").lower().rstrip(".")
                    q+=nl
            p+=ln
    except Exception:return None

def tls_sni(buf):
    if len(buf)<5 or buf[0]!=0x16 or buf[1]!=3:return None
    p=5
    while p+5<=len(buf):
        typ=buf[p];ln=struct.unpack("!H",buf[p+3:p+5])[0]
        if p+5+ln>len(buf):break
        if typ==22:
            hs=buf[p+5:p+5+ln];q=0
            while q+4<=len(hs):
                hl=int.from_bytes(hs[q+1:q+4],"big");total=4+hl
                if q+total>len(hs):break
                if hs[q]==1:
                    s=parse_sni(hs[q:q+total])
                    if s:return s
                q+=total
        p+=5+ln
    low=bytes(buf).lower()
    for c in ROUTES:
        if c.encode() in low:return c
    return None

async def initial(reader):
    b=bytearray();deadline=asyncio.get_running_loop().time()+INITIAL_TIMEOUT
    while len(b)<MAX_INITIAL:
        try:x=await asyncio.wait_for(reader.read(min(8192,MAX_INITIAL-len(b))),max(.05,deadline-asyncio.get_running_loop().time()))
        except asyncio.TimeoutError:break
        if not x:break
        b.extend(x)
        if bytes(b).startswith(HTTP_METHODS) and (b"\r\n\r\n" in b or len(b)>8192):break
        if len(b)>=5 and b[0]==0x16 and b[1]==3 and tls_sni(b):break
        if b[:1]!=b"\x16":break
    return bytes(b)

async def pipe(r,w,label):
    try:
        while True:
            b=await asyncio.wait_for(r.read(65536),IDLE_TIMEOUT)
            if not b:return
            w.write(b);await w.drain()
    except asyncio.CancelledError:raise
    except Exception as e:log.warning("RELAY_ERROR direction=%s error=%s:%s",label,type(e).__name__,e)

async def relay(r,w,first,dest,label,sni="-"):
    up=None;tasks=set()
    try:
        log.warning("ROUTE_SELECTED route=%s sni=%s dest=%s:%d initial=%d",label,sni,dest[0],dest[1],len(first))
        ur,up=await asyncio.wait_for(asyncio.open_connection(*dest),UPSTREAM_TIMEOUT)
        log.warning("UPSTREAM_CONNECT_OK route=%s dest=%s:%d",label,dest[0],dest[1])
        if first:up.write(first);await up.drain();log.warning("INITIAL_FORWARDED route=%s bytes=%d",label,len(first))
        tasks={asyncio.create_task(pipe(r,up,"client->upstream")),asyncio.create_task(pipe(ur,w,"upstream->client"))}
        await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
    except asyncio.TimeoutError:log.warning("UPSTREAM_TIMEOUT route=%s dest=%s:%d",label,dest[0],dest[1])
    except Exception as e:log.warning("RELAY_ERROR route=%s error=%s:%s",label,type(e).__name__,e)
    finally:
        for t in tasks:
            if not t.done():t.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        for s in (w,up):
            if s:
                try:s.close();await s.wait_closed()
                except Exception:pass

async def response(w,status,body=b"",ctype=b"text/plain; charset=utf-8"):
    h=b"HTTP/1.1 "+status+b"\r\nContent-Type: "+ctype+b"\r\nContent-Length: "+str(len(body)).encode()+b"\r\nCache-Control: no-store, no-cache, must-revalidate, max-age=0\r\nPragma: no-cache\r\nExpires: 0\r\nConnection: close\r\n\r\n"
    w.write(h+body);await w.drain()

async def http(r,w,first):
    head=first.decode("latin1","ignore").split("\r\n");parts=head[0].split(" ",2);method=parts[0] if parts else "";target=parts[1] if len(parts)>1 else "";path=urllib.parse.urlsplit(target).path
    if method in ("GET","HEAD") and path in ("/health","/ready"):
        ok,why=(True,"ready") if path=="/health" else readiness();body=b"healthy\n" if path=="/health" else (b"ready\n" if ok else ("not-ready:"+why+"\n").encode());await response(w,b"200 OK" if ok else b"503 Service Unavailable",b"" if method=="HEAD" else body);return
    m=re.fullmatch(r"/sub/([A-Za-z0-9_-]{20,128})/?",path)
    if method in ("GET","HEAD") and m:
        payload,status=subscription(urllib.parse.unquote(m.group(1)))
        if payload is not None:await response(w,b"200 OK",b"" if method=="HEAD" else payload,b"text/plain; charset=utf-8")
        else:await response(w,b"404 Not Found" if status=="TOKEN_INVALID" else b"500 Internal Server Error",(status+"\n").encode())
        return
    if method in ("GET","HEAD") and path in ("/","/index.html"):
        body=SITE.read_bytes();await response(w,b"200 OK",b"" if method=="HEAD" else body,b"text/html; charset=utf-8");return
    await relay(r,w,first,HTTP_DEST,"http-xhttp")

async def handle(r,w):
    peer=w.get_extra_info("peername")
    async with SEM:
        try:
            first=await initial(r)
            if not first:return
            if first.startswith(HTTP_METHODS):await http(r,w,first);return
            if first[:2]==b"\x16\x03":
                s=tls_sni(first);route=ROUTES.get(s or "");log.warning("TLS_SNI peer=%s sni=%s",peer,s or "-")
                if route:await relay(r,w,first,(route[0],route[1]),route[2],s)
                else:log.warning("ROUTE_REJECT tls_sni=%s",s or "-")
            else:log.warning("ROUTE_REJECT unknown_protocol=0x%s",first[:1].hex())
        except Exception as e:log.warning("ERROR peer=%s error=%s:%s",peer,type(e).__name__,e)
        finally:
            try:w.close();await w.wait_closed()
            except Exception:pass

async def main():
    ok,why=readiness()
    if not ok:raise SystemExit("GATEWAY_START_BLOCKED readiness="+why)
    server=await asyncio.start_server(handle,"0.0.0.0",PORT,limit=262144);log.warning("READY port=%d max_connections=%d",PORT,MAX_CONNECTIONS)
    async with server:await server.serve_forever()
if __name__=="__main__":asyncio.run(main())
