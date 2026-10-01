"""Open the existing local map; reuse its server without installing anything."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8871/research_data/five_province_history/UNIFIED_MAP.html'
MARKER = '<title>แผนที่วิเคราะห์ทุเรียน • ดิน อากาศ ฤดูกาล</title>'.encode()

def report_url(port=8871):
    return f'http://127.0.0.1:{port}/research_data/five_province_history/UNIFIED_MAP.html'

def server_ready(port=8871):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/project', timeout=2) as response:
            identity=json.load(response)
        expected=hashlib.sha256(ROOT.resolve().as_posix().casefold().encode()).hexdigest()
        if (identity.get('application')!='orchard-analysis' or identity.get('protocol')!=1
            or identity.get('workspace_id')!=expected):return False
        with urlopen(report_url(port), timeout=2) as response:
            return response.status == 200 and MARKER in response.read()[:2048]
    except (URLError, OSError, ValueError, AttributeError):
        return False

def port_occupied(port):
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex(('127.0.0.1',port)) == 0

def choose_port(preferred=8871):
    """Reuse only this checkout; leave other servers running and choose a free port."""
    candidates=list(range(preferred,min(preferred+9,65536)))
    occupied={port:port_occupied(port) for port in candidates}
    for port in candidates:
        if occupied[port] and server_ready(port):return port
    for port in candidates:
        if not occupied[port]:return port
    raise RuntimeError('No free report port. Retry with --port 8890. No process was stopped.')

def ensure_server(port=8871):
    if server_ready(port):
        return 'existing'
    if port_occupied(port):
        raise RuntimeError(f'Port {port} is occupied by a different/unready page. No process was stopped.')
    log_dir = ROOT / '.build'
    log_dir.mkdir(exist_ok=True)
    with (log_dir/'report_server.log').open('ab') as log:
        child = subprocess.Popen([sys.executable,str(ROOT/'tools/serve_orchard_analysis.py'),'--port',str(port)],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    for _ in range(40):
        if server_ready(port):
            return 'started'
        if child.poll() is not None:
            raise RuntimeError('Server stopped. See .build/report_server.log')
        time.sleep(0.25)
    raise RuntimeError('Server not ready yet. See .build/report_server.log and retry.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Read-only readiness check; do not start or open anything')
    parser.add_argument('--port',type=int,default=8871,help='First of up to nine local ports to try')
    parser.add_argument('--no-browser',action='store_true',help='Start/check the server without opening a browser')
    args = parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Port must be between 1024 and 65535')
    if args.check:
        ready = any(server_ready(port) for port in range(args.port,min(args.port+9,65536)))
        print('ready' if ready else 'not ready')
        return 0 if ready else 1
    try:
        port=choose_port(args.port)
        state = ensure_server(port)
        url=report_url(port)
        print(f'Workspace: {ROOT}\nServer: {state}\n{url}')
        if not args.no_browser and not webbrowser.open(url):
            print('Open the URL above in your browser.')
        return 0
    except Exception as exc:
        print(f'Cannot open report: {exc}',file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
